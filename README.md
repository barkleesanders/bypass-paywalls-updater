# Bypass Paywalls Chrome Clean Updater

This repository contains a simple Python script to help you keep your "Bypass Paywalls Chrome Clean" extension updated automatically.

**Important:** Due to Chrome's security policies, this script can **download** the latest version for you, but you will still need to **manually install** it into your Chrome browser.

## How it Works

The script checks the official download source for the "Bypass Paywalls Chrome Clean" extension. It detects changes using HTTP headers in this priority order:

1. **ETag** -- the most reliable change indicator
2. **Last-Modified** -- timestamp-based detection
3. **Content-Length** -- file size fallback

When a change is detected, the script downloads the `.zip` file, verifies it is a valid ZIP archive, and saves it to your Downloads folder. The previous check state is stored as a JSON file so the script knows what has changed since last run.

## Features

- **Reliable change detection** via ETag and Last-Modified headers (Content-Length fallback)
- **Download integrity verification** -- confirms the file is a valid ZIP before saving
- **Automatic retry** with exponential backoff on network failures
- **Structured logging** with timestamps (useful for cron job output)
- **Desktop notifications** on macOS when a new version is downloaded
- **CLI options** for `--force`, `--dry-run`, `--download-dir`, and more
- **Environment variable configuration** for cron-friendly setups
- **Legacy state migration** -- automatically upgrades from the old format

## Getting Started (For Everyone!)

Don't worry if you're not a tech expert. Just follow these steps carefully.

### Quick Start for macOS Users (One-Line Command)

If you're on a Mac, you can get started with just one line of code in your Terminal! This command will download the script, install what it needs, and run it for the first time.

1.  Open your "Terminal" application (you can find it in Applications > Utilities).
2.  Copy and paste the entire line below into the Terminal and press Enter:

    ```bash
    cd ~ && git clone https://github.com/barkleesanders/bypass-paywalls-updater.git && cd bypass-paywalls-updater && python3 -m pip install requests --user --break-system-packages && python3 update_bypass_paywalls.py
    ```

    The script will then check for updates and download the extension to your "Downloads" folder if a new version is available. After it finishes, proceed to **Step 4: Install the Extension in Chrome (Manual Step)** below.

    If you encounter any issues, please refer to the "Troubleshooting" section.

### Step 1: Download the Script

1.  Go to the script's page on GitHub: [https://github.com/barkleesanders/bypass-paywalls-updater](https://github.com/barkleesanders/bypass-paywalls-updater)
2.  Click on the green "Code" button.
3.  Select "Download ZIP".
4.  Unzip the downloaded file to a location on your computer where you want to keep the script (e.g., your Documents folder, or a new folder like `C:\BypassUpdater` on Windows, or `~/Documents/BypassUpdater` on macOS/Linux).

### Step 2: Make sure Python is Installed

This script needs Python to run. Most modern computers (especially macOS and Linux) come with Python pre-installed. If you're on Windows, you might need to install it.

To check if you have Python, open your computer's "Terminal" (on macOS/Linux) or "Command Prompt" / "PowerShell" (on Windows) and type:

```bash
python3 --version
```

If you see a version number (like `Python 3.x.x`), you're good to go! If not, you'll need to install Python 3. You can download it from the official website: [python.org](https://www.python.org/downloads/)

### Step 3: Run the Script for the First Time (Manual Check)

1.  Open your computer's "Terminal" (macOS/Linux) or "Command Prompt" / "PowerShell" (Windows).
2.  Navigate to the folder where you unzipped the script. For example, if you put it in `~/Documents/BypassUpdater` on macOS, you'd type:
    ```bash
    cd ~/Documents/BypassUpdater
    ```
    On Windows, if you put it in `C:\BypassUpdater`, you'd type:
    ```bash
    cd C:\BypassUpdater
    ```
3.  Run the script by typing:
    ```bash
    python3 update_bypass_paywalls.py
    ```

    The script will check for updates. If it finds a new version (or if it's the first time running), it will download the `bypass-paywalls-chrome-clean-master.zip` file to your computer's "Downloads" folder.

### Step 4: Install the Extension in Chrome (Manual Step)

**This step MUST be done manually every time a new version is downloaded.**

1.  Open Google Chrome.
2.  Type `chrome://extensions` into the address bar and press Enter.
3.  In the top right corner, make sure "Developer mode" is **toggled ON**.
4.  Open your computer's "Downloads" folder.
5.  Find the downloaded file: `bypass-paywalls-chrome-clean-master.zip`.
6.  **Drag and drop** this `.zip` file directly onto the `chrome://extensions` page in Chrome.
7.  Chrome will prompt you to confirm the installation. Click "Add extension".

### Step 5: Automate Daily Checks (Optional, for macOS/Linux Users)

If you're on macOS or Linux, you can set up your computer to run this script automatically every day. This uses a system feature called `cron`.

1.  Open your "Terminal" application.
2.  Type `crontab -e` and press Enter. This will open a text editor.
3.  Add the following line to the very end of the file. This will run the script every day at 3:00 AM with desktop notifications enabled:
    ```
    0 3 * * * /usr/bin/python3 /path/to/update_bypass_paywalls.py --notify 2>&1
    ```
    **Important:** Replace `/path/to/` with the actual path to the script. You can find the correct path to `python3` by typing `which python3` in your terminal.
4.  Save and close the file:
    *   If using `nano`: Press `Ctrl + X`, then `Y` to confirm saving, then Enter.
    *   If using `vi`: Press `Esc`, then type `:wq` and press Enter.

Now, your computer will automatically check for updates daily! You'll still need to manually install the extension in Chrome when a new version is downloaded.

## Command-Line Options

```
python3 update_bypass_paywalls.py [OPTIONS]

Options:
  --force           Skip change detection and download regardless
  --dry-run         Check for changes but do not download
  --download-dir    Directory to save the ZIP (default: ~/Downloads)
  --state-file      Path to the JSON state file (default: ~/.bpc_updater_state.json)
  --notify          Send a macOS desktop notification on successful download
  -v, --verbose     Enable debug-level logging
```

## Environment Variables

These can be used instead of (or in addition to) command-line options. Command-line options take precedence.

| Variable          | Description                                   | Default                         |
|-------------------|-----------------------------------------------|---------------------------------|
| `BPC_DOWNLOAD_DIR`| Directory to save the downloaded ZIP           | `~/Downloads`                   |
| `BPC_STATE_FILE`  | Path to the JSON state file                    | `~/.bpc_updater_state.json`     |
| `BPC_NOTIFY`      | Set to `1` to enable macOS desktop notifications | disabled                      |

## Troubleshooting

*   **"No such file or directory" error when running the script:** Double-check that you are in the correct directory in your Terminal/Command Prompt, and that the script file name is correct.
*   **Script doesn't download anything:** Run the script with `--verbose` for detailed output: `python3 update_bypass_paywalls.py --verbose`. Check the output for any error messages. Also, ensure your internet connection is working.
*   **Chrome won't install the .zip file:** Make sure "Developer mode" is enabled on your `chrome://extensions` page. Also, ensure you are dragging the `.zip` file directly onto the extensions page, not just into the Chrome window.
*   **Network errors:** The script automatically retries up to 3 times with increasing delays. If it still fails, check your internet connection and try again later.
*   **"Corrupt state file" warning:** The script will automatically start fresh. This can happen after a manual edit of the state file. No action needed.

## License

This script is provided as-is, without warranty. It's a simple tool to help you manage your extension updates. The "Bypass Paywalls Chrome Clean" extension itself is governed by its own license (MIT License).
