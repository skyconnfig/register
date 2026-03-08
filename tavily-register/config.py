"""
配置文件
"""

# Tavily相关配置
TAVILY_HOME_URL = "https://app.tavily.com/home"
TAVILY_SIGNUP_URL = "https://app.tavily.com/home"

# 邮箱配置
EMAIL_DOMAIN = "2925.com"
EMAIL_PREFIX = "user123"  # 请替换为您的邮箱前缀
MAIN_EMAIL = f"{EMAIL_PREFIX}@{EMAIL_DOMAIN}"

# 2925.com邮箱访问配置
EMAIL_CHECK_URL = "https://2925.com"

# 注册配置
DEFAULT_PASSWORD = "TavilyAuto123!"

# 文件路径
API_KEYS_FILE = "api_keys.md"
COOKIES_FILE = "email_cookies.json"

# 等待时间配置（秒）
WAIT_TIME_SHORT = 2
WAIT_TIME_MEDIUM = 5
WAIT_TIME_LONG = 10
EMAIL_CHECK_INTERVAL = 30
MAX_EMAIL_WAIT_TIME = 300  # 5分钟

# 浏览器配置
HEADLESS = False  # 设置为True可以无头模式运行
BROWSER_TIMEOUT = 30000  # 30秒
BROWSER_TYPE = "firefox"  # 可选: "chromium", "firefox", "webkit"
