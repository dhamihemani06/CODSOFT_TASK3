"""
ContactVault Pro — Advanced Contact Book
Python 3.10+ | Tkinter GUI | SQLite database | No third-party packages

Features:
- Add, view, search, update, and delete contacts
- Store name, phone, email, address, company, and notes
- Persistent SQLite database
- Search across name, phone, email, and company
- Input validation for phone number and email
- Sortable contact table
- Export contacts to CSV
- Contact details viewer
- Duplicate phone number warning
"""

from __future__ import annotations

import csv
import re
import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

DB_PATH = Path(__file__).with_name("contacts.db")


class ContactDatabase:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._setup()

    def _setup(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL DEFAULT '',
                address TEXT NOT NULL DEFAULT '',
                company TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name COLLATE NOCASE)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_contacts_phone ON contacts(phone)")
        self.conn.commit()

    def list_contacts(self, search: str = "") -> list[sqlite3.Row]:
        term = f"%{search.strip()}%"
        if search.strip():
            return self.conn.execute("""
                SELECT * FROM contacts
                WHERE name LIKE ? COLLATE NOCASE
                   OR phone LIKE ?
                   OR email LIKE ? COLLATE NOCASE
                   OR company LIKE ? COLLATE NOCASE
                ORDER BY name COLLATE NOCASE
            """, (term, term, term, term)).fetchall()
        return self.conn.execute(
            "SELECT * FROM contacts ORDER BY name COLLATE NOCASE"
        ).fetchall()

    def get(self, contact_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM contacts WHERE id=?", (contact_id,)).fetchone()

    def phone_exists(self, phone: str, exclude_id: int | None = None) -> bool:
        if exclude_id is None:
            row = self.conn.execute("SELECT id FROM contacts WHERE phone=?", (phone,)).fetchone()
        else:
            row = self.conn.execute(
                "SELECT id FROM contacts WHERE phone=? AND id<>?", (phone, exclude_id)
            ).fetchone()
        return row is not None

    def add(self, data: dict[str, str]) -> None:
        self.conn.execute("""
            INSERT INTO contacts (name, phone, email, address, company, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (data["name"], data["phone"], data["email"], data["address"],
              data["company"], data["notes"]))
        self.conn.commit()

    def update(self, contact_id: int, data: dict[str, str]) -> None:
        self.conn.execute("""
            UPDATE contacts SET name=?, phone=?, email=?, address=?, company=?,
                notes=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (data["name"], data["phone"], data["email"], data["address"],
              data["company"], data["notes"], contact_id))
        self.conn.commit()

    def delete(self, contact_id: int) -> None:
        self.conn.execute("DELETE FROM contacts WHERE id=?", (contact_id,))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()


def validate_contact(data: dict[str, str]) -> str | None:
    if not data["name"]:
        return "Name is required."
    if not data["phone"]:
        return "Phone number is required."
    digits = re.sub(r"\D", "", data["phone"])
    if len(digits) < 7 or len(digits) > 15:
        return "Enter a phone number containing 7 to 15 digits."
    if data["email"] and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", data["email"]):
        return "Enter a valid email address, or leave the email field blank."
    return None


class ContactDialog(tk.Toplevel):
    FIELDS = (
        ("name", "Full name *"),
        ("phone", "Phone number *"),
        ("email", "Email"),
        ("address", "Address"),
        ("company", "Company / organization"),
        ("notes", "Notes"),
    )

    def __init__(self, parent: tk.Misc, contact: sqlite3.Row | None = None) -> None:
        super().__init__(parent)
        self.result: dict[str, str] | None = None
        self.title("Edit contact" if contact else "Add contact")
        self.configure(bg="#f3f6f8")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.vars: dict[str, tk.StringVar] = {}
        frame = ttk.Frame(self, padding=20)
        frame.grid(sticky="nsew")
        frame.columnconfigure(1, weight=1)

        for index, (key, label) in enumerate(self.FIELDS):
            value = contact[key] if contact else ""
            var = tk.StringVar(value=value)
            self.vars[key] = var
            ttk.Label(frame, text=label).grid(row=index, column=0, sticky="w", padx=(0, 14), pady=7)
            if key in ("address", "notes"):
                widget = tk.Text(frame, width=36, height=2, wrap="word", font=("Segoe UI", 10))
                widget.insert("1.0", value)
                widget.grid(row=index, column=1, sticky="ew", pady=5)
                setattr(self, f"{key}_widget", widget)
            else:
                entry = ttk.Entry(frame, textvariable=var, width=38)
                entry.grid(row=index, column=1, sticky="ew", pady=5)
                if index == 0:
                    first_entry = entry

        buttons = ttk.Frame(frame)
        buttons.grid(row=len(self.FIELDS), column=0, columnspan=2, sticky="e", pady=(15, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Save contact", command=self._save).pack(side="right")
        if contact is None:
            first_entry.focus_set()
        self.bind("<Escape>", lambda _event: self.destroy())
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx()+60}+{parent.winfo_rooty()+40}")

    def _save(self) -> None:
        data = {key: var.get().strip() for key, var in self.vars.items()}
        data["address"] = self.address_widget.get("1.0", "end-1c").strip()
        data["notes"] = self.notes_widget.get("1.0", "end-1c").strip()
        error = validate_contact(data)
        if error:
            messagebox.showwarning("Check contact details", error, parent=self)
            return
        data["phone"] = re.sub(r"\s+", " ", data["phone"])
        self.result = data
        self.destroy()


class ContactVaultApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.db = ContactDatabase()
        self.title("ContactVault Pro | Contact Manager")
        self.geometry("1120x700")
        self.minsize(900, 570)
        self.configure(bg="#f3f6f8")
        self._style()
        self._build()
        self.refresh()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#f3f6f8")
        style.configure("TLabel", background="#f3f6f8", foreground="#172b35", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 23, "bold"), foreground="#185641")
        style.configure("Sub.TLabel", foreground="#687984", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=(9, 7))
        style.configure("Primary.TButton", background="#176548", foreground="white", padding=(11, 8))
        style.map("Primary.TButton", background=[("active", "#124c37")])
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=31,
                        background="white", fieldbackground="white")
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), padding=8)

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=(24, 20, 24, 18))
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x")
        title_box = ttk.Frame(header)
        title_box.pack(side="left", fill="x", expand=True)
        ttk.Label(title_box, text="ContactVault Pro", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_box, text="All your important connections, organized in one place.",
                  style="Sub.TLabel").pack(anchor="w", pady=(3, 0))
        ttk.Button(header, text="＋ Add Contact", style="Primary.TButton",
                   command=self.add_contact).pack(side="right", padx=(8, 0))
        ttk.Button(header, text="Export CSV", command=self.export_csv).pack(side="right")

        stats = ttk.Frame(outer)
        stats.pack(fill="x", pady=(20, 16))
        self.total_var = tk.StringVar(value="0")
        self.visible_var = tk.StringVar(value="0")
        self.with_email_var = tk.StringVar(value="0")
        for index, (label, var, color) in enumerate((
            ("TOTAL CONTACTS", self.total_var, "#e1eee8"),
            ("MATCHING RESULTS", self.visible_var, "#e5edf9"),
            ("WITH EMAIL", self.with_email_var, "#fff0d8"),
        )):
            card = tk.Frame(stats, bg=color, padx=16, pady=11)
            card.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 10, 0))
            stats.columnconfigure(index, weight=1)
            tk.Label(card, text=label, bg=color, fg="#596b73",
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")
            tk.Label(card, textvariable=var, bg=color, fg="#172b35",
                     font=("Segoe UI", 21, "bold")).pack(anchor="w", pady=(3, 0))

        search_row = ttk.Frame(outer)
        search_row.pack(fill="x", pady=(0, 12))
        ttk.Label(search_row, text="Search contacts").pack(side="left", padx=(0, 8))
        self.search_var = tk.StringVar()
        search = ttk.Entry(search_row, textvariable=self.search_var, width=42)
        search.pack(side="left", fill="x", expand=True)
        ttk.Button(search_row, text="Clear search", command=lambda: self.search_var.set("")).pack(side="left", padx=8)
        ttk.Label(search_row, text="Search by name, phone, email, or company",
                  style="Sub.TLabel").pack(side="right")

        table_frame = ttk.Frame(outer)
        table_frame.pack(fill="both", expand=True)
        columns = ("name", "phone", "email", "company", "address")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        config = {
            "name": ("Name", 210), "phone": ("Phone number", 150),
            "email": ("Email", 220), "company": ("Company", 170), "address": ("Address", 240),
        }
        for key, (heading, width) in config.items():
            self.tree.heading(key, text=heading, command=lambda col=key: self.sort_by(col))
            self.tree.column(key, width=width, minwidth=90, anchor="w")
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", lambda _event: self.view_contact())

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(14, 0))
        ttk.Button(actions, text="View details", command=self.view_contact).pack(side="left")
        ttk.Button(actions, text="Edit selected", command=self.edit_contact).pack(side="left", padx=8)
        ttk.Button(actions, text="Delete selected", command=self.delete_contact).pack(side="left")
        self.footer_var = tk.StringVar(value="Contacts are saved locally on this computer.")
        ttk.Label(actions, textvariable=self.footer_var, style="Sub.TLabel").pack(side="right")

        self.search_var.trace_add("write", lambda *_args: self.refresh())

    def refresh(self) -> None:
        contacts = self.db.list_contacts(self.search_var.get())
        all_contacts = self.db.list_contacts()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for contact in contacts:
            self.tree.insert("", "end", iid=str(contact["id"]),
                             values=(contact["name"], contact["phone"], contact["email"],
                                     contact["company"], contact["address"].replace("\n", ", ")))
        self.total_var.set(str(len(all_contacts)))
        self.visible_var.set(str(len(contacts)))
        self.with_email_var.set(str(sum(bool(c["email"]) for c in all_contacts)))
        self.footer_var.set(f"Showing {len(contacts)} of {len(all_contacts)} contact(s) • Saved locally")

    def selected_contact(self) -> sqlite3.Row | None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Select a contact", "Please select a contact first.", parent=self)
            return None
        return self.db.get(int(selection[0]))

    def add_contact(self) -> None:
        dialog = ContactDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            if self.db.phone_exists(dialog.result["phone"]):
                if not messagebox.askyesno("Possible duplicate",
                    "A contact with this exact phone number already exists. Add anyway?", parent=self):
                    return
            self.db.add(dialog.result)
            self.refresh()

    def edit_contact(self) -> None:
        contact = self.selected_contact()
        if contact is None:
            return
        dialog = ContactDialog(self, contact)
        self.wait_window(dialog)
        if dialog.result:
            if self.db.phone_exists(dialog.result["phone"], contact["id"]):
                if not messagebox.askyesno("Possible duplicate",
                    "Another contact uses this exact phone number. Save anyway?", parent=self):
                    return
            self.db.update(contact["id"], dialog.result)
            self.refresh()
            self.tree.selection_set(str(contact["id"]))

    def delete_contact(self) -> None:
        contact = self.selected_contact()
        if contact is None:
            return
        if messagebox.askyesno("Delete contact",
            f"Delete {contact['name']} permanently?", parent=self):
            self.db.delete(contact["id"])
            self.refresh()

    def view_contact(self) -> None:
        contact = self.selected_contact()
        if contact is None:
            return
        details = (
            f"Name: {contact['name']}\n"
            f"Phone: {contact['phone']}\n"
            f"Email: {contact['email'] or '—'}\n"
            f"Address: {contact['address'] or '—'}\n"
            f"Company: {contact['company'] or '—'}\n"
            f"Notes: {contact['notes'] or '—'}\n\n"
            f"Created: {contact['created_at']}\n"
            f"Last updated: {contact['updated_at']}"
        )
        messagebox.showinfo("Contact details", details, parent=self)

    def sort_by(self, column: str) -> None:
        items = [(self.tree.set(item, column).casefold(), item) for item in self.tree.get_children()]
        reverse = getattr(self, "_sort_reverse", {}).get(column, False)
        items.sort(reverse=reverse)
        for index, (_value, item) in enumerate(items):
            self.tree.move(item, "", index)
        if not hasattr(self, "_sort_reverse"):
            self._sort_reverse = {}
        self._sort_reverse[column] = not reverse

    def export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self, title="Export contacts", defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
            initialfile="contactvault_contacts.csv",
        )
        if not path:
            return
        contacts = self.db.list_contacts()
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow(("ID", "Name", "Phone", "Email", "Address", "Company",
                                 "Notes", "Created At", "Updated At"))
                for c in contacts:
                    writer.writerow((c["id"], c["name"], c["phone"], c["email"], c["address"],
                                     c["company"], c["notes"], c["created_at"], c["updated_at"]))
        except OSError as exc:
            messagebox.showerror("Export failed", f"Could not save the file:\n{exc}", parent=self)
            return
        messagebox.showinfo("Export complete", f"Exported {len(contacts)} contact(s) to:\n{path}", parent=self)

    def _close(self) -> None:
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    ContactVaultApp().mainloop()
