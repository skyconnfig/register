#!/usr/bin/env python3
"""
2925.com邮箱登录助手
专门用于登录2925.com邮箱并保存cookies
"""
import json
import time
from playwright.sync_api import sync_playwright
from config import *
from utils import save_cookies, load_cookies, wait_with_message


class EmailLoginHelper:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        
    def start_browser(self):
        """启动浏览器"""
        self.playwright = sync_playwright().start()
        
        # 根据配置选择浏览器类型
        if BROWSER_TYPE == "firefox":
            self.browser = self.playwright.firefox.launch(headless=False)  # 强制显示浏览器
        elif BROWSER_TYPE == "webkit":
            self.browser = self.playwright.webkit.launch(headless=False)
        else:  # chromium
            browser_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
            self.browser = self.playwright.chromium.launch(
                headless=False,  # 强制显示浏览器
                args=browser_args
            )
        
        self.page = self.browser.new_page()
        self.page.set_default_timeout(BROWSER_TIMEOUT)
        
    def close_browser(self):
        """关闭浏览器"""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def explore_email_site(self):
        """探索2925.com邮箱网站结构"""
        try:
            print(f"🌐 正在访问邮箱网站: {EMAIL_CHECK_URL}")
            self.page.goto(EMAIL_CHECK_URL)
            wait_with_message(5, "等待页面加载")
            
            print("📋 页面标题:", self.page.title())
            print("📋 页面URL:", self.page.url)
            
            # 尝试查找邮箱相关的元素
            print("\n🔍 查找页面元素...")
            
            # 查找输入框
            input_elements = self.page.query_selector_all('input')
            print(f"📝 找到 {len(input_elements)} 个输入框:")
            for i, input_elem in enumerate(input_elements[:10]):  # 只显示前10个
                try:
                    input_type = input_elem.get_attribute('type') or 'text'
                    placeholder = input_elem.get_attribute('placeholder') or ''
                    name = input_elem.get_attribute('name') or ''
                    id_attr = input_elem.get_attribute('id') or ''
                    print(f"  {i+1}. type={input_type}, placeholder='{placeholder}', name='{name}', id='{id_attr}'")
                except:
                    print(f"  {i+1}. (无法获取属性)")
            
            # 查找按钮
            button_elements = self.page.query_selector_all('button, input[type="submit"], input[type="button"]')
            print(f"\n🔘 找到 {len(button_elements)} 个按钮:")
            for i, btn in enumerate(button_elements[:10]):  # 只显示前10个
                try:
                    text = btn.inner_text() or btn.get_attribute('value') or ''
                    btn_type = btn.get_attribute('type') or ''
                    print(f"  {i+1}. text='{text}', type='{btn_type}'")
                except:
                    print(f"  {i+1}. (无法获取文本)")
            
            # 查找链接
            link_elements = self.page.query_selector_all('a')
            print(f"\n🔗 找到 {len(link_elements)} 个链接:")
            for i, link in enumerate(link_elements[:10]):  # 只显示前10个
                try:
                    text = link.inner_text().strip()
                    href = link.get_attribute('href') or ''
                    if text and len(text) < 50:  # 只显示有意义的短文本
                        print(f"  {i+1}. text='{text}', href='{href}'")
                except:
                    continue
            
            return True
            
        except Exception as e:
            print(f"❌ 探索网站失败: {e}")
            return False
    
    def manual_login_guide(self):
        """手动登录指导"""
        print("\n" + "="*60)
        print("📖 手动登录指导")
        print("="*60)
        print(f"1. 当前页面: {self.page.url}")
        print(f"2. 目标邮箱: {MAIN_EMAIL}")
        print("3. 请在浏览器中手动完成以下操作:")
        print("   - 找到邮箱输入框")
        print(f"   - 输入邮箱地址: {MAIN_EMAIL}")
        print("   - 点击登录/访问按钮")
        print("   - 等待进入邮箱界面")
        print("4. 完成后按Enter键继续...")
        
        input("按Enter键继续...")
        
        # 保存当前cookies
        try:
            cookies = self.page.context.cookies()

            # 直接保存到JSON文件（与cookie_manager.py相同的方式）
            with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)

            print(f"✅ 成功保存 {len(cookies)} 个cookies到 {COOKIES_FILE}")

            # 显示关键cookies信息
            print("\n📋 关键cookies信息:")
            for cookie in cookies:
                if cookie['name'] in ['aut', 'session', 'token', 'auth']:
                    print(f"  {cookie['name']}: {cookie['value'][:20]}...")

            # 显示当前页面信息
            print(f"\n📋 当前页面: {self.page.title()}")
            print(f"📋 当前URL: {self.page.url}")

            return True
        except Exception as e:
            print(f"❌ 保存cookies失败: {e}")
            return False
    
    def test_saved_cookies(self):
        """测试已保存的cookies"""
        try:
            print("\n🧪 测试已保存的cookies...")
            
            # 加载cookies
            cookies = load_cookies(COOKIES_FILE)
            if not cookies:
                print("❌ 没有找到已保存的cookies")
                return False
            
            print(f"📂 加载了 {len(cookies)} 个cookies")
            
            # 打开新页面并应用cookies
            test_page = self.browser.new_page()
            test_page.context.add_cookies(cookies)
            
            # 访问邮箱网站
            test_page.goto(EMAIL_CHECK_URL)
            wait_with_message(3, "等待页面加载")
            
            print(f"✅ 测试页面标题: {test_page.title()}")
            print(f"✅ 测试页面URL: {test_page.url}")
            
            # 检查是否成功登录（这里需要根据实际网站调整）
            # 可以查找特定的元素来判断是否已登录
            
            test_page.close()
            return True
            
        except Exception as e:
            print(f"❌ 测试cookies失败: {e}")
            return False
    
    def interactive_email_setup(self):
        """交互式邮箱设置"""
        print("🚀 开始2925.com邮箱设置...")
        print("="*50)
        
        # 步骤1: 探索网站
        print("\n📋 步骤1: 探索网站结构...")
        if not self.explore_email_site():
            return False
        
        # 步骤2: 手动登录指导
        print("\n📋 步骤2: 手动登录...")
        if not self.manual_login_guide():
            return False
        
        # 步骤3: 测试cookies
        print("\n📋 步骤3: 测试cookies...")
        if not self.test_saved_cookies():
            print("⚠️ cookies测试失败，但已保存，可以在主程序中尝试使用")
        
        print("\n🎉 邮箱设置完成!")
        print(f"💾 cookies已保存到: {COOKIES_FILE}")
        print("💡 现在可以运行主程序进行自动注册")
        
        return True


def main():
    """主函数"""
    helper = EmailLoginHelper()
    
    try:
        helper.start_browser()
        helper.interactive_email_setup()
        
        # 询问是否要保持浏览器打开
        keep_open = input("\n是否保持浏览器打开以便进一步测试? (y/n): ").lower().strip()
        if keep_open == 'y':
            print("浏览器将保持打开状态，请手动关闭...")
            input("按Enter键退出程序...")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断了程序")
    except Exception as e:
        print(f"\n❌ 程序出错: {e}")
    finally:
        if input("\n是否关闭浏览器? (y/n): ").lower().strip() != 'n':
            helper.close_browser()


if __name__ == "__main__":
    main()
