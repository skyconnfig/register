#!/usr/bin/env python3
"""
智能Tavily自动化模块
基于深层HTML信息分析，使用智能元素检测和等待机制
"""
import time
from playwright.sync_api import sync_playwright
from config import *
from utils import generate_email, save_api_key


class IntelligentTavilyAutomation:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.email = None
        self.password = DEFAULT_PASSWORD
        self.debug = True
        self.email_prefix = None  # 动态邮箱前缀
        self.headless_mode = None  # 记住headless设置
        
        # 基于深层分析的智能选择器配置
        self.selectors = {
            'signup_button': {
                'primary': [
                    'a:has-text("Sign up")',  # 最稳定：基于文本内容
                    'a[href*="signup"]',      # 稳定：基于URL特征
                ],
                'fallback': [
                    'p:has-text("Don\'t have an account?") a',  # 基于父元素上下文
                    'a[class*="c7c2d7b15"]',  # 基于部分class（如果稳定）
                ]
            },
            'email_input': {
                'primary': [
                    'input#email',                    # 最稳定：基于ID
                    'input[name="email"]',            # 最稳定：基于name
                    'input[type="text"][autocomplete="email"]',  # 稳定：组合属性
                ],
                'fallback': [
                    'form._form-signup-id input[type="text"]',  # 基于表单上下文
                    'label:has-text("Email address") + div input',  # 基于标签关联
                ]
            },
            'continue_button': {
                'primary': [
                    'button[name="action"][type="submit"]',  # 最稳定：精确属性组合
                    'button[type="submit"]:has-text("Continue")',  # 稳定：类型+文本
                ],
                'fallback': [
                    'form._form-signup-id button[type="submit"]',  # 基于表单上下文
                    'button._button-signup-id',  # 基于特定class
                ]
            },
            'password_input': {
                'primary': [
                    'input#password',                 # 最稳定：基于ID
                    'input[name="password"]',         # 最稳定：基于name
                    'input[type="password"][autocomplete="new-password"]',  # 稳定：组合属性
                ],
                'fallback': [
                    'input[type="password"]',         # 基于类型
                    'label:has-text("Password") + div input',  # 基于标签关联
                ]
            },
            'submit_button': {
                'primary': [
                    'button[name="action"][type="submit"]',  # 复用continue按钮逻辑
                    'button[type="submit"]:has-text("Continue")',
                ],
                'fallback': [
                    'button[type="submit"]',
                    'input[type="submit"]',
                ]
            }
        }
    
    def log(self, message, level="INFO"):
        """调试日志"""
        if self.debug:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] {level}: {message}")
    
    def start_browser(self, headless=None):
        """启动浏览器"""
        self.playwright = sync_playwright().start()
        headless_mode = headless if headless is not None else HEADLESS

        # 记住headless设置，供后续使用
        self.headless_mode = headless_mode

        if BROWSER_TYPE == "firefox":
            self.browser = self.playwright.firefox.launch(headless=headless_mode)
        elif BROWSER_TYPE == "webkit":
            self.browser = self.playwright.webkit.launch(headless=headless_mode)
        else:  # chromium
            browser_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
            self.browser = self.playwright.chromium.launch(
                headless=headless_mode,
                args=browser_args
            )

        self.page = self.browser.new_page()
        self.page.set_default_timeout(30000)
    
    def close_browser(self):
        """关闭浏览器"""
        try:
            if self.page:
                self.page.close()
                self.page = None
            if self.browser:
                self.browser.close()
                self.browser = None
            if self.playwright:
                self.playwright.stop()
                self.playwright = None
        except Exception as e:
            # 浏览器可能已经关闭，忽略错误
            self.log(f"⚠️ 浏览器关闭时出现错误（可忽略）: {e}", "DEBUG")
            pass
    
    def smart_wait_for_element(self, element_config, timeout=30000):
        """智能等待元素出现"""
        primary_selectors = element_config['primary']
        fallback_selectors = element_config['fallback']
        
        # 首先尝试主要选择器
        for selector in primary_selectors:
            try:
                self.log(f"🔍 尝试主要选择器: {selector}")
                element = self.page.wait_for_selector(selector, timeout=timeout//len(primary_selectors))
                if element:
                    self.log(f"✅ 找到元素: {selector}")
                    return element, selector
            except Exception as e:
                self.log(f"❌ 主要选择器失败: {selector}")
                continue
        
        # 如果主要选择器都失败，尝试备用选择器
        self.log("⚠️ 主要选择器都失败，尝试备用选择器...")
        for selector in fallback_selectors:
            try:
                self.log(f"🔍 尝试备用选择器: {selector}")
                element = self.page.wait_for_selector(selector, timeout=timeout//len(fallback_selectors))
                if element:
                    self.log(f"✅ 找到元素（备用）: {selector}")
                    return element, selector
            except Exception as e:
                self.log(f"❌ 备用选择器失败: {selector}")
                continue
        
        return None, None
    
    def smart_click(self, element_name, retries=3):
        """智能点击元素"""
        element_config = self.selectors.get(element_name)
        if not element_config:
            self.log(f"❌ 未找到元素配置: {element_name}")
            return False
        
        for attempt in range(retries):
            self.log(f"🔄 尝试点击 {element_name} (第 {attempt+1}/{retries} 次)")
            
            element, selector = self.smart_wait_for_element(element_config)
            
            if element:
                try:
                    # 确保元素可见和稳定
                    element.wait_for_element_state('visible', timeout=5000)
                    element.wait_for_element_state('stable', timeout=5000)
                    
                    # 点击元素
                    element.click()
                    self.log(f"✅ 成功点击 {element_name}")

                    # 增加1秒延迟确保操作稳定
                    time.sleep(1)

                    # 等待页面响应
                    self.page.wait_for_load_state('networkidle', timeout=10000)
                    return True
                    
                except Exception as e:
                    self.log(f"❌ 点击失败: {e}")
            
            # 如果失败，刷新页面重试
            if attempt < retries - 1:
                self.log("🔄 刷新页面后重试...")
                self.page.reload()
                self.page.wait_for_load_state('networkidle')
                time.sleep(2)
        
        self.log(f"❌ 最终未能点击 {element_name}")
        return False
    
    def smart_fill(self, element_name, text, retries=3):
        """智能填写输入框"""
        element_config = self.selectors.get(element_name)
        if not element_config:
            self.log(f"❌ 未找到元素配置: {element_name}")
            return False
        
        for attempt in range(retries):
            self.log(f"🔄 尝试填写 {element_name} (第 {attempt+1}/{retries} 次)")
            
            element, selector = self.smart_wait_for_element(element_config)
            
            if element:
                try:
                    # 确保元素可见和可编辑
                    element.wait_for_element_state('visible', timeout=5000)
                    element.wait_for_element_state('editable', timeout=5000)
                    
                    # 清空并填写
                    element.fill('')  # 先清空
                    element.fill(text)
                    
                    # 增加1秒延迟确保填写稳定
                    time.sleep(1)

                    # 验证填写结果
                    filled_value = element.input_value()
                    if filled_value == text:
                        self.log(f"✅ 成功填写 {element_name}: {text}")
                        return True
                    else:
                        self.log(f"⚠️ 填写验证失败: 期望 '{text}', 实际 '{filled_value}'")
                        
                except Exception as e:
                    self.log(f"❌ 填写失败: {e}")
            
            # 如果失败，刷新页面重试
            if attempt < retries - 1:
                self.log("🔄 刷新页面后重试...")
                self.page.reload()
                self.page.wait_for_load_state('networkidle')
                time.sleep(2)
        
        self.log(f"❌ 最终未能填写 {element_name}")
        return False
    
    def navigate_to_signup(self):
        """导航到注册页面"""
        try:
            self.log("🌐 正在访问Tavily主页...")
            self.page.goto(TAVILY_HOME_URL)
            self.page.wait_for_load_state('networkidle')
            
            # 智能点击Sign Up按钮
            if self.smart_click('signup_button'):
                self.log("✅ 成功导航到注册页面")
                return True
            else:
                # 备选方案：直接访问注册页面
                self.log("⚠️ 未找到Sign Up按钮，尝试直接访问注册页面...")
                self.page.goto(TAVILY_SIGNUP_URL)
                self.page.wait_for_load_state('networkidle')
                return True
                
        except Exception as e:
            self.log(f"❌ 导航到注册页面失败: {e}")
            return False
    
    def fill_registration_form(self):
        """填写注册表单"""
        try:
            # 生成随机邮箱（使用动态前缀）
            self.email = generate_email(self.email_prefix)
            self.log(f"📧 生成的注册邮箱: {self.email}")
            
            # 智能填写邮箱
            if not self.smart_fill('email_input', self.email):
                return False
            
            # 智能点击继续按钮
            if not self.smart_click('continue_button'):
                return False
            
            self.log("✅ 注册表单填写完成")
            return True
            
        except Exception as e:
            self.log(f"❌ 填写注册表单失败: {e}")
            return False
    
    def fill_password(self):
        """填写密码"""
        try:
            self.log("🔐 正在填写密码...")
            
            # 智能填写密码
            if not self.smart_fill('password_input', self.password):
                return False
            
            # 智能点击提交按钮
            if not self.smart_click('submit_button'):
                return False
            
            self.log("✅ 密码填写完成")
            return True
            
        except Exception as e:
            self.log(f"❌ 填写密码失败: {e}")
            return False
    
    def run_registration(self):
        """运行完整的智能注册流程"""
        try:
            self.log("🚀 开始智能注册流程...")

            if not self.navigate_to_signup():
                raise Exception("导航到注册页面失败")

            if not self.fill_registration_form():
                raise Exception("填写注册表单失败")

            if not self.fill_password():
                raise Exception("填写密码失败")

            self.log("🎉 智能注册流程完成!")
            return True

        except Exception as e:
            self.log(f"❌ 智能注册流程失败: {e}")
            return False

    def run_complete_automation(self):
        """运行完整的智能自动化流程：注册 + 邮件验证 + API key获取"""
        try:
            self.log("🚀 开始完整的智能自动化流程...")

            # 步骤1: 注册账户
            self.log("📋 步骤1: 智能注册账户...")
            if not self.run_registration():
                raise Exception("注册流程失败")

            # 步骤2: 邮件验证和登录
            self.log("📋 步骤2: 邮件验证和登录...")
            api_key = self.handle_email_verification_and_login()

            if api_key:
                self.log(f"🎉 完整自动化流程成功完成!")
                self.log(f"📧 注册邮箱: {self.email}")
                self.log(f"🔐 密码: {self.password}")
                self.log(f"🔑 API Key: {api_key}")

                # 保存API key
                save_api_key(self.email, api_key, self.password)
                return api_key
            else:
                raise Exception("邮件验证或API key获取失败")

        except Exception as e:
            self.log(f"❌ 完整自动化流程失败: {e}")
            return None

    def handle_email_verification_and_login(self):
        """处理邮件验证和登录，返回API key"""
        try:
            # 导入邮件检查器
            from email_checker import EmailChecker

            self.log("📧 初始化邮件检查器（共用当前浏览器上下文）...")
            email_checker = EmailChecker()

            # 复用当前浏览器与页面，不关闭（避免二次登录）
            email_checker.attach_to(self.playwright, self.browser, self.page)

            try:
                # 加载邮箱页面
                self.log("📧 加载邮箱页面...")
                email_checker.load_email_page()

                # 查找验证邮件
                self.log(f"🔍 查找验证邮件: {self.email}")
                verification_link = email_checker.check_for_tavily_email(self.email)

                if not verification_link:
                    raise Exception("未找到验证邮件")

                self.log(f"✅ 找到验证链接: {verification_link}")

                # 访问验证链接
                self.log("🔗 访问验证链接...")
                result = email_checker.navigate_to_verification_link(verification_link)

                if result == "login_required":
                    self.log("🔑 需要登录Tavily账户...")
                    if not email_checker.login_to_tavily(self.email, self.password):
                        raise Exception("Tavily登录失败")
                    self.log("✅ Tavily登录成功!")

                # 获取API key
                self.log("🔑 获取API key...")
                api_key = email_checker.get_api_key_from_tavily()

                if api_key:
                    self.log(f"🎉 成功获取API key: {api_key}")
                    return api_key
                else:
                    raise Exception("未能获取API key")

            finally:
                email_checker.close_browser()

        except Exception as e:
            self.log(f"❌ 邮件验证和登录失败: {e}")
            return None
