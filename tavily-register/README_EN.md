# Tavily API Key Automation Tool

English | [中文](README.md)

<details>
<summary>Changelog</summary>

- 2025-08-19: Introduced single-window reuse (EmailChecker.attach_to + managed_externally). Complete registration, email verification, and API acquisition within the same browser context to preserve login state and cache, reducing instability from re-login and stale elements; improved dialog handling listeners and logging.

</details>


An intelligent automation solution based on deep HTML analysis for end-to-end Tavily API Key acquisition.

## Quick Start

### Requirements

- Python 3.7+
- Internet connection
- 2925.com email account

### Installation

```bash
# Clone the project
git clone https://github.com/yatotm/tavily-register.git
cd tavily-register

# Auto install dependencies
python setup.py

# Or manual installation
pip install -r requirements.txt
playwright install firefox
```

### Configuration

1. **Set Email Prefix**

   Edit `config.py`:
   ```python
   EMAIL_PREFIX = "your_prefix"  # Replace with your 2925.com email prefix
   ```

2. **Setup Email Login**
   ```bash
   python email_login_helper.py
   ```
   Follow the prompts to complete 2925.com email login and save cookies.

### Run

```bash
python main.py
```

Choose running mode:
- **Intelligent Automation Mode** (Recommended): Efficient and stable automation process
- **Test Mode**: Traditional approach for debugging and HTML information collection

## Project Structure

```
tavily-register/
├── main.py                          # Main program entry
├── intelligent_tavily_automation.py  # Intelligent automation core
├── email_checker.py                 # Email verification and login
├── email_login_helper.py            # Email login assistant
├── tavily_automation.py             # Traditional automation module
├── config.py                        # Configuration file
├── utils.py                         # Utility functions
├── requirements.txt                 # Dependencies list
├── setup.py                         # Installation script
├── api_keys.md                      # API Key storage file
└── email_cookies.json               # Email cookies
```

## Workflow

- Supports end-to-end single-window reuse (Registration → Email Verification → Login → API acquisition) to avoid re-login and improve stability

1. **Registration**: Automatically fill Tavily registration form
2. **Email Verification**: Intelligently detect verification emails and click verification links (reusing the current page)
3. **Login**: Automatically login to Tavily account
4. **API Acquisition**: Intelligently identify and obtain API Key
5. **Data Storage**: Save account information and API Key to file

## Output Format

API Keys are saved in `api_keys.md` file:
```
user123-abc123@2925.com,TavilyAuto123!,tvly-dev-xxxxxxxxxx,2025-01-01 12:00:00;
```

Format: `Email,Password,API_Key,Timestamp`

<details>
<summary>Troubleshooting</summary>

### Common Issues

**Browser Launch Failed**
- Run: `playwright install firefox`
- Check internet connection

**Email Login Issues**
- Re-run: `python email_login_helper.py`
- Ensure 2925.com email service is working

**Verification Email Not Found**
- Check if email prefix is set correctly
- Manually visit 2925.com to check emails

**API Key Acquisition Failed**
- Check if successfully logged into Tavily
- Review generated screenshot files

**Encountered CAPTCHA/Human Verification**
- If IP purity or environmental factors trigger human verification
- Choose frontend mode (browser mode option 1)
- Manually complete verification and the program will continue automatically
- Recommend using clean network environment and IP address

</details>

<details>
<summary>Configuration Options</summary>

### Browser Configuration
```python
HEADLESS = False          # Whether to run in headless mode
BROWSER_TYPE = "firefox"  # Browser type
```

### Wait Time Configuration
```python
WAIT_TIME_SHORT = 2       # Short wait time
WAIT_TIME_MEDIUM = 5      # Medium wait time
WAIT_TIME_LONG = 10       # Long wait time
```

### Email Configuration
```python
EMAIL_DOMAIN = "2925.com"
EMAIL_PREFIX = "user123"  # Your email prefix
```

</details>

## Tech Stack

- **Python 3.7+**
- **Playwright**: Web automation
- **BeautifulSoup4**: HTML parsing

## Disclaimer

This tool is for educational and research purposes only. Please comply with the terms of service of relevant websites when using.

## License

MIT License
