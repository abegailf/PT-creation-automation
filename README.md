# Problem Template Creation Automato

This project contains a Python script that automates the creation of Problem Templates (PTs) and their subproblems on the Mathspace admin platform. It uses Playwright to drive a web browser, reading all the necessary data from a local XML file (`sample_pt.xml`).

## Prerequisites

*   Python 3.8 or newer
*   Access to the Mathspace admin panel

## Setup Instructions

Following these steps will set up the project in an isolated environment, which is the recommended approach.

### 1. Create and Activate a Virtual Environment

A virtual environment (`venv`) is **highly recommended** for this project. It isolates the necessary packages (like Playwright) from your computer's global Python installation. This prevents version conflicts between different projects and keeps your system clean.

**On Windows:**

```sh
# Create the virtual environment in a folder named 'venv'
python -m venv venv

# Activate it
.\venv\Scripts\activate
```

**On macOS / Linux:**

```sh
# Create the virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate
```

You will know the `venv` is active when you see `(venv)` at the beginning of your terminal prompt.

### 2. Install Dependencies

Install the required Python packages, including Playwright.

```sh
pip install -r requirements.txt
```

### 3. Install Playwright Browsers

Playwright requires its own browser binaries. This command downloads the version of Chromium that the script will use.

```sh
playwright install
```

### 4. Generate the Authentication File

To avoid logging in every time, you need to generate an `auth.json` file that stores your session cookies.

1.  Run the `save_auth.py` script:
    ```sh
    python save_auth.py
    ```
2.  The script will open a browser window and navigate to the Mathspace login page.
3.  **Log in manually** as you normally would.
4.  Once you have successfully logged in, **close the script** by pressing `Ctrl+C` in your terminal.

This will create an `auth.json` file in your project directory. You only need to do this once, or whenever your session expires.

## How to Run the Automator

1.  Ensure your virtual environment is active.
2.  Customize the `sample_pt.xml` file with the content you wish to upload.
3.  Run the `pt_automator.py` script:
    ```sh
    python pt_automator.py
    ```
4.  The script will prompt you to enter the "Base Subtopic" ID. Enter the ID and press `Enter`.
5.  The browser will launch and begin filling out the forms automatically.
6.  Once complete, the script will wait for you to press `Enter` in the terminal before closing the browser.

## Customization

All content for the Problem Template, including instructions, variables, subproblems, and steps, is controlled by the `sample_pt.xml` file. You can edit this file to change the data that gets uploaded.
