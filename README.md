# ContactVault Pro — Advanced Python Contact Book

ContactVault Pro is a desktop contact manager built with Python, Tkinter, and SQLite. It expands the basic contact-book assignment into a complete CRUD application.

## Features

- Add, view, update, and delete contacts
- Store name, phone number, email, address, company, and notes
- Persistent SQLite database
- Search by name, phone number, email, or company
- Validate required fields, phone numbers, and email addresses
- Warn about possible duplicate phone numbers
- Sort visible contacts by clicking table headings
- Dashboard statistics
- Export all contacts to CSV
- No third-party packages required

## Requirements

- Python 3.10 or newer
- Tkinter (normally included with Python)
- SQLite (included with Python)

## Run

1. Extract the ZIP archive.
2. Open a terminal in the `ContactVault_Pro` folder.
3. Run:

   ```bash
   python contact_book.py
   ```

The application creates `contacts.db` automatically on first launch.

## Project structure

```text
ContactVault_Pro/
├── contact_book.py   # GUI, validation, database logic and CSV export
├── README.md         # Setup and usage instructions
└── requirements.txt  # No third-party packages required
```

## Concepts demonstrated

- Object-oriented programming
- Tkinter GUI and event-driven programming
- SQLite database and parameterized SQL
- CRUD operations
- Input validation and regular expressions
- Search, sorting, and data export
- Exception handling
- Separation of database, validation, and interface logic

## Future enhancements

- Contact profile photos
- Import contacts from CSV
- Birthday reminders
- Contact groups and favourites
- Password-protected access
- Cloud synchronisation and automated backups
