#!/usr/bin/env python3
"""
邮箱验证邮件检查器
专门用于检查2925.com邮箱中的验证邮件
"""
import re
import time
from playwright.sync_api import sync_playwright
from config import *
from utils import load_cookies, wait_with_message


class EmailChecker:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.managed_externally = False  # 若由外部传入页面/上下文，则不在此类中关闭浏览器
        
    def start_browser(self, headless=None):
        """启动浏览器"""
        self.playwright = sync_playwright().start()

        # 使用传入的headless参数，如果没有则使用配置文件默认值
        headless_mode = headless if headless is not None else HEADLESS

        # 根据配置选择浏览器类型
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
        self.page.set_default_timeout(BROWSER_TIMEOUT)

        # 设置弹窗处理
        self.page.on("dialog", self.handle_dialog)

    def attach_to(self, playwright, browser, page):
        """附着到外部已存在的Playwright上下文/浏览器/页面，复用同一窗口"""
        self.playwright = playwright
        self.browser = browser
        self.page = page
        self.managed_externally = True
        # 补充必要的默认配置与监听
        if self.page:
            try:
                self.page.set_default_timeout(BROWSER_TIMEOUT)
                self.page.on("dialog", self.handle_dialog)
            except Exception:
                pass

    def handle_dialog(self, dialog):
        """处理弹窗"""
        try:
            print(f"🔔 检测到弹窗: {dialog.message}")
            if "第三方网站跳转提醒" in dialog.message or "即将离开" in dialog.message:
                print("✅ 确认跳转到验证页面")
                dialog.accept()
            else:
                print("❌ 取消弹窗")
                dialog.dismiss()
        except Exception as e:
            print(f"⚠️ 处理弹窗失败: {e}")
            try:
                dialog.dismiss()
            except:
                pass

    def close_browser(self):
        """关闭浏览器（仅在本类管理浏览器时关闭）"""
        if self.managed_externally:
            return
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def load_email_page(self):
        """加载邮箱页面"""
        try:
            # 先访问主域名
            print("🌐 访问主域名...")
            self.page.goto("https://www.2925.com")
            wait_with_message(1, "等待主域名加载")

            # 加载已保存的cookies
            cookies = load_cookies(COOKIES_FILE)
            if cookies:
                print("📂 加载已保存的cookies...")
                self.page.context.add_cookies(cookies)

                # 刷新页面以应用cookies
                print("🔄 刷新页面...")
                self.page.reload()
                wait_with_message(2, "等待cookies生效")

            # 导航到邮件列表页面
            maillist_url = "https://www.2925.com/#/mailList"
            print(f"📧 导航到邮件列表: {maillist_url}")
            self.page.goto(maillist_url)
            wait_with_message(3, "等待邮件列表加载")

            # 检查是否成功登录
            current_url = self.page.url
            if "login" in current_url.lower() or "signin" in current_url.lower():
                print("❌ 仍在登录页面，cookies可能已过期")
                return False

            print(f"✅ 页面加载完成: {self.page.title()}")
            print("✅ 成功访问邮件列表页面")
            return True

        except Exception as e:
            print(f"❌ 加载邮箱页面失败: {e}")
            return False
    
    def find_emails_on_page(self):
        """在当前页面查找邮件"""
        try:
            # 等待邮件列表加载
            wait_with_message(2, "等待邮件列表加载")

            # 查找邮件行
            email_rows = self.page.query_selector_all('tbody tr')

            if not email_rows:
                print("⚠️ 未找到邮件行")
                return []

            print(f"✅ 找到 {len(email_rows)} 个邮件行")
            emails_found = []

            for i, row in enumerate(email_rows[:15]):  # 检查前15个邮件
                try:
                    # 获取邮件文本内容
                    text = row.inner_text()
                    if not text or len(text.strip()) < 10:
                        continue

                    # 检查是否有未读标识（邮箱小图标）
                    # 根据用户反馈，真正的未读邮件标识是 <use xlink:href="#unread_mail">
                    is_unread = False

                    # 查找SVG未读图标
                    svg_elements = row.query_selector_all('svg.svg-common.icon-svg-small')
                    for svg in svg_elements:
                        try:
                            # 查找use元素
                            use_element = svg.query_selector('use')
                            if use_element:
                                xlink_href = use_element.get_attribute('xlink:href')
                                if xlink_href == '#unread_mail':
                                    is_unread = True
                                    print(f"🔍 在第{i+1}个邮件中找到未读标识: xlink:href='{xlink_href}'")
                                    break
                        except:
                            continue

                    # 备用检测方法
                    if not is_unread:
                        # 检查是否有包含unread_mail的use元素
                        use_elements = row.query_selector_all('use[xlink\\:href="#unread_mail"]')
                        if use_elements:
                            is_unread = True
                            print(f"🔍 在第{i+1}个邮件中找到未读标识: use[xlink:href='#unread_mail']")

                    # 也可以通过样式类判断
                    if not is_unread:
                        row_class = row.get_attribute('class') or ''
                        if 'unread' in row_class.lower() or 'new' in row_class.lower():
                            is_unread = True

                    emails_found.append({
                        'element': row,
                        'text': text.strip(),
                        'index': i,
                        'is_unread': is_unread
                    })

                except Exception as e:
                    print(f"⚠️ 处理邮件行 {i} 时出错: {e}")
                    continue

            print(f"📋 成功解析 {len(emails_found)} 个邮件")
            return emails_found

        except Exception as e:
            print(f"❌ 查找邮件失败: {e}")
            return []
    
    def check_for_tavily_email(self, target_email, max_retries=10, wait_interval=30):
        """检查Tavily验证邮件（支持等待新邮件和别名验证）"""
        try:
            print(f"📧 开始检查验证邮件，目标邮箱: {target_email}")
            print(f"⏳ 最大重试次数: {max_retries}, 等待间隔: {wait_interval}秒")

            # 提取目标邮箱的别名部分
            target_alias = target_email.split('@')[0] if '@' in target_email else target_email
            print(f"🎯 目标别名: {target_alias}")

            for retry in range(max_retries):
                print(f"\n🔄 第 {retry + 1}/{max_retries} 次检查...")

                # 查找页面上的邮件
                emails = self.find_emails_on_page()

                if not emails:
                    print("⚠️ 未在页面上找到任何邮件元素")
                    if retry < max_retries - 1:
                        print(f"⏳ 等待 {wait_interval} 秒后重试...")
                        wait_with_message(wait_interval, f"等待新邮件到达")
                        self.refresh_email_list()
                        continue
                    else:
                        return None

                print(f"📋 找到 {len(emails)} 个邮件，正在检查...")

                # 首先查找未读的Tavily验证邮件
                unread_tavily_emails = []
                read_tavily_emails = []

                for email_info in emails:
                    text = email_info['text'].lower()
                    original_text = email_info['text']

                    # 检查是否是Tavily验证邮件
                    is_tavily = 'tavily' in text
                    is_verify = any(keyword in text for keyword in ['verify your email', 'verify', 'verification'])

                    if is_tavily and is_verify:
                        if email_info['is_unread']:
                            unread_tavily_emails.append(email_info)
                            print(f"✅ 找到未读Tavily验证邮件! (第{email_info['index']+1}个)")
                        else:
                            read_tavily_emails.append(email_info)
                            print(f"📖 找到已读Tavily验证邮件 (第{email_info['index']+1}个)")

                # 如果有未读邮件，只处理第一个未读邮件
                if unread_tavily_emails:
                    print(f"🎯 找到 {len(unread_tavily_emails)} 个未读Tavily验证邮件，处理第一个")

                    first_unread_email = unread_tavily_emails[0]
                    verification_link = self.process_email_with_alias_check(first_unread_email, target_alias)
                    if verification_link:
                        return verification_link

                    # 如果第一个邮件别名不匹配，进入快速刷新模式
                    print("⚠️ 第一个未读邮件别名不匹配，进入快速刷新模式...")
                    return self.quick_refresh_mode(target_alias, max_refresh_time=60, refresh_interval=10)

                # 如果没有未读邮件，使用智能等待
                elif retry == 0:
                    print("⚠️ 没有找到未读的Tavily验证邮件，启用智能等待...")
                    if self.smart_wait_for_new_email(target_alias):
                        print("✅ 智能等待检测到新邮件，继续检查")
                        continue
                    else:
                        print("⚠️ 智能等待未检测到新邮件，使用常规等待")
                        if retry < max_retries - 1:
                            print(f"⏳ 等待 {wait_interval} 秒后重试...")
                            wait_with_message(wait_interval, f"等待新邮件到达")
                            self.refresh_email_list()
                            continue

                # 如果多次重试后仍然没有未读邮件，处理已读邮件
                elif read_tavily_emails and retry >= 3:
                    print(f"⚠️ 多次重试后仍无未读邮件，尝试处理已读邮件...")

                    for email_info in read_tavily_emails:
                        verification_link = self.process_email_with_alias_check(email_info, target_alias)
                        if verification_link:
                            return verification_link

                # 如果这次没有找到合适的邮件，继续等待
                if retry < max_retries - 1:
                    print(f"⏳ 等待 {wait_interval} 秒后重试...")
                    wait_with_message(wait_interval, f"等待新邮件到达")
                    self.refresh_email_list()

            print("❌ 达到最大重试次数，未找到匹配的Tavily验证邮件")
            return None

        except Exception as e:
            print(f"❌ 检查验证邮件失败: {e}")
            return None

    def refresh_email_list(self):
        """刷新邮件列表"""
        try:
            print("🔄 刷新邮件列表...")
            # 刷新页面
            self.page.reload()
            wait_with_message(3, "等待页面重新加载")

            # 或者点击刷新按钮（如果存在）
            refresh_selectors = [
                'button[title*="refresh" i]',
                'button[title*="刷新" i]',
                'button:has-text("刷新")',
                'button:has-text("Refresh")',
                '.refresh-btn',
                '[data-testid="refresh"]'
            ]

            for selector in refresh_selectors:
                try:
                    refresh_btn = self.page.query_selector(selector)
                    if refresh_btn:
                        print(f"✅ 找到刷新按钮: {selector}")
                        refresh_btn.click()
                        wait_with_message(2, "等待刷新完成")
                        return
                except:
                    continue

            print("✅ 页面刷新完成")

        except Exception as e:
            print(f"⚠️ 刷新邮件列表失败: {e}")

    def process_email_with_alias_check(self, email_info, target_alias):
        """处理邮件并验证别名"""
        try:
            original_text = email_info['text']
            status = "未读" if email_info['is_unread'] else "已读"

            print(f"📧 处理{status}邮件: {original_text[:100]}...")

            # 首先尝试从预览文本中直接提取验证链接
            verification_link = self.extract_link_from_text(original_text)
            if verification_link:
                print(f"✅ 从预览文本中提取到验证链接: {verification_link}")
                # 即使从预览中找到链接，也要验证别名
                if self.verify_email_alias_from_preview(email_info, target_alias):
                    return verification_link
                else:
                    print("⚠️ 预览文本别名不匹配，跳过此邮件")
                    return None

            # 如果预览文本中没有找到，点击邮件获取完整内容
            try:
                print("🔍 点击邮件获取完整内容...")
                email_info['element'].click()
                wait_with_message(3, "等待邮件打开")

                # 验证邮件别名
                if not self.verify_email_alias_in_detail(target_alias):
                    print(f"❌ 邮件别名不匹配目标别名 {target_alias}，返回邮件列表")
                    self.return_to_email_list()
                    return None

                # 别名匹配，提取验证链接
                verification_link = self.extract_verification_link()
                if verification_link:
                    print(f"✅ 找到匹配的验证链接: {verification_link}")
                    return verification_link
                else:
                    print("⚠️ 未在邮件详情中找到验证链接")
                    self.return_to_email_list()
                    return None

            except Exception as e:
                print(f"⚠️ 点击邮件失败: {e}")
                return None

        except Exception as e:
            print(f"❌ 处理邮件失败: {e}")
            return None

    def verify_email_alias_from_preview(self, email_info, target_alias):
        """从预览信息验证邮件别名（简单检查）"""
        try:
            # 在预览文本中查找目标别名
            text = email_info['text'].lower()
            if target_alias.lower() in text:
                print(f"✅ 预览文本中找到目标别名: {target_alias}")
                return True
            else:
                print(f"⚠️ 预览文本中未找到目标别名: {target_alias}")
                return False
        except Exception as e:
            print(f"⚠️ 验证预览别名失败: {e}")
            return False

    def verify_email_alias_in_detail(self, target_alias):
        """在邮件详情页面验证别名"""
        try:
            print(f"🔍 验证邮件别名是否为: {target_alias}")

            # 查找邮件用户信息容器
            alias_selectors = [
                '.mail-user-list-container .user-button-name',
                '.user-button-name',
                '[data-v-223b96f0].user-button-name',
                '.mail-user-list-container span',
                '.user-button span'
            ]

            for selector in alias_selectors:
                try:
                    alias_elements = self.page.query_selector_all(selector)
                    for element in alias_elements:
                        alias_text = element.inner_text().strip()
                        print(f"📋 找到别名元素: {alias_text}")

                        if alias_text == target_alias:
                            print(f"✅ 别名匹配: {alias_text} == {target_alias}")
                            return True
                        elif target_alias in alias_text:
                            print(f"✅ 别名部分匹配: {target_alias} in {alias_text}")
                            return True

                except Exception as e:
                    continue

            # 如果没有找到专门的别名元素，在整个页面中搜索
            print("🔍 在整个页面中搜索目标别名...")
            page_content = self.page.content()
            if target_alias in page_content:
                print(f"✅ 在页面内容中找到目标别名: {target_alias}")
                return True

            print(f"❌ 未找到目标别名: {target_alias}")
            return False

        except Exception as e:
            print(f"❌ 验证邮件别名失败: {e}")
            return False

    def return_to_email_list(self):
        """返回邮件列表页面"""
        try:
            print("🔙 返回邮件列表...")

            # 尝试多种返回方式
            back_selectors = [
                'button:has-text("返回")',
                'button:has-text("Back")',
                '.back-btn',
                '[data-testid="back"]',
                'button[title*="back" i]',
                'button[title*="返回" i]'
            ]

            for selector in back_selectors:
                try:
                    back_btn = self.page.query_selector(selector)
                    if back_btn:
                        print(f"✅ 找到返回按钮: {selector}")
                        back_btn.click()
                        wait_with_message(2, "等待返回邮件列表")
                        return True
                except:
                    continue

            # 如果没有找到返回按钮，直接导航到邮件列表页面
            print("⚠️ 未找到返回按钮，直接导航到邮件列表页面")
            self.page.goto("https://www.2925.com/#/mailList")
            wait_with_message(3, "等待邮件列表页面加载")
            return True

        except Exception as e:
            print(f"❌ 返回邮件列表失败: {e}")
            return False

    def quick_refresh_mode(self, target_alias, max_refresh_time=60, refresh_interval=10):
        """快速刷新模式：每10秒刷新一次，检查第一个未读Tavily邮件"""
        try:
            print(f"🔄 进入快速刷新模式")
            print(f"⏰ 最大刷新时间: {max_refresh_time}秒, 刷新间隔: {refresh_interval}秒")

            start_time = time.time()
            refresh_count = 0
            max_refreshes = max_refresh_time // refresh_interval

            while refresh_count < max_refreshes:
                refresh_count += 1
                elapsed_time = time.time() - start_time

                print(f"\n🔄 快速刷新 {refresh_count}/{max_refreshes} (已用时 {elapsed_time:.0f}秒)")

                # 使用智能等待替代固定等待
                print("👀 启用智能监控新邮件提示...")
                if self.monitor_new_email_notification(max_wait_time=refresh_interval):
                    print("🎉 检测到新邮件提示，立即刷新")
                else:
                    print(f"⏰ {refresh_interval}秒内未检测到新邮件提示，进行常规刷新")

                # 刷新邮件列表
                self.refresh_email_list()

                # 查找邮件
                emails = self.find_emails_on_page()
                if not emails:
                    print("⚠️ 刷新后未找到邮件")
                    continue

                # 检查第一个邮件是否是未读的Tavily验证邮件
                first_email = emails[0]
                text = first_email['text'].lower()

                is_tavily = 'tavily' in text
                is_verify = any(keyword in text for keyword in ['verify your email', 'verify', 'verification'])
                is_unread = first_email['is_unread']

                if is_tavily and is_verify and is_unread:
                    print(f"✅ 发现新的未读Tavily验证邮件在第一位!")
                    print(f"📧 邮件内容: {first_email['text'][:100]}...")

                    # 处理这个邮件
                    verification_link = self.process_email_with_alias_check(first_email, target_alias)
                    if verification_link:
                        print(f"🎉 快速刷新模式成功找到匹配邮件!")
                        return verification_link
                    else:
                        print("⚠️ 新邮件别名仍不匹配，继续刷新...")
                else:
                    status = []
                    if not is_tavily:
                        status.append("非Tavily")
                    if not is_verify:
                        status.append("非验证邮件")
                    if not is_unread:
                        status.append("已读")

                    print(f"⚠️ 第一个邮件不符合条件: {', '.join(status)}")
                    print(f"📧 第一个邮件: {first_email['text'][:50]}...")

            print(f"⏰ 快速刷新模式超时 ({max_refresh_time}秒)，未找到匹配的新邮件")
            return None

        except Exception as e:
            print(f"❌ 快速刷新模式失败: {e}")
            return None

    def monitor_new_email_notification(self, max_wait_time=60):
        """监控新邮件提示浮动元素"""
        try:
            print(f"👀 开始监控新邮件提示，最大等待时间: {max_wait_time}秒")

            # 新邮件提示的选择器
            notification_selectors = [
                '.notice-mail.clearfix',
                'div[class*="notice-mail"]',
                '.notice-mail',
                '[data-v-2b7186e8].notice-mail'
            ]

            start_time = time.time()

            while time.time() - start_time < max_wait_time:
                # 检查新邮件提示
                for selector in notification_selectors:
                    try:
                        notification = self.page.query_selector(selector)
                        if notification:
                            # 检查是否包含新邮件信息
                            notification_text = notification.inner_text().lower()
                            if '新邮件' in notification_text or 'unread' in notification_text:
                                print(f"🎉 检测到新邮件提示: {notification_text[:50]}...")

                                # 点击关闭提示（如果有关闭按钮）
                                try:
                                    close_btn = notification.query_selector('.notice-close, [class*="close"]')
                                    if close_btn:
                                        close_btn.click()
                                        print("✅ 已关闭新邮件提示")
                                except:
                                    pass

                                return True
                    except:
                        continue

                # 每秒检查一次
                time.sleep(1)

            print(f"⏰ 监控超时 ({max_wait_time}秒)，未检测到新邮件提示")
            return False

        except Exception as e:
            print(f"❌ 监控新邮件提示失败: {e}")
            return False

    def smart_wait_for_new_email(self, target_alias):
        """智能等待新邮件（优先监控提示，备用定时刷新）"""
        try:
            print("🧠 启动智能新邮件等待模式")

            # 首先检查当前是否有未读邮件
            emails = self.find_emails_on_page()
            if emails:
                for email_info in emails:
                    text = email_info['text'].lower()
                    is_tavily = 'tavily' in text
                    is_verify = any(keyword in text for keyword in ['verify your email', 'verify', 'verification'])
                    is_unread = email_info['is_unread']

                    if is_tavily and is_verify and is_unread:
                        print("✅ 发现当前就有未读Tavily邮件")
                        return True

            # 如果没有未读邮件，开始监控新邮件提示
            print("📧 当前无未读Tavily邮件，开始监控新邮件提示...")

            if self.monitor_new_email_notification(max_wait_time=60):
                print("🔄 检测到新邮件提示，立即刷新页面")
                self.refresh_email_list()
                return True
            else:
                print("⏰ 未检测到新邮件提示，进行常规刷新")
                self.refresh_email_list()
                return False

        except Exception as e:
            print(f"❌ 智能等待新邮件失败: {e}")
            return False
    
    def extract_verification_link(self):
        """从邮件内容中提取验证链接"""
        try:
            wait_with_message(2, "等待邮件内容加载")

            print("🔍 开始查找验证链接...")

            # 方法1: 查找所有链接元素
            links = self.page.query_selector_all('a')
            print(f"📋 找到 {len(links)} 个链接元素")

            for i, link in enumerate(links):
                try:
                    href = link.get_attribute('href')
                    text = link.inner_text().strip()

                    print(f"  链接{i+1}: href='{href}', text='{text}'")

                    if href and 'tavily.com' in href.lower():
                        if any(keyword in href.lower() for keyword in ['verify', 'confirm', 'activate', 'email-verification']):
                            print(f"✅ 找到Tavily验证链接: {href}")
                            return href
                        elif any(keyword in text.lower() for keyword in ['verify', 'confirm', 'activate', '验证']):
                            print(f"✅ 找到验证按钮链接: {href}")
                            return href
                except Exception as e:
                    print(f"  处理链接{i+1}时出错: {e}")
                    continue

            # 方法2: 查找按钮元素
            buttons = self.page.query_selector_all('button, input[type="button"], input[type="submit"]')
            print(f"📋 找到 {len(buttons)} 个按钮元素")

            for i, button in enumerate(buttons):
                try:
                    onclick = button.get_attribute('onclick') or ''
                    text = button.inner_text().strip()

                    print(f"  按钮{i+1}: onclick='{onclick}', text='{text}'")

                    if 'tavily.com' in onclick and 'verify' in onclick.lower():
                        # 从onclick中提取链接
                        import re
                        url_match = re.search(r'https://[^\'"]+', onclick)
                        if url_match:
                            link = url_match.group(0)
                            print(f"✅ 从按钮onclick中提取到验证链接: {link}")
                            return link
                except Exception as e:
                    print(f"  处理按钮{i+1}时出错: {e}")
                    continue

            # 方法3: 从页面文本中提取
            print("🔍 尝试从页面文本中提取链接...")
            page_content = self.page.inner_text('body')

            # 使用更精确的正则表达式
            patterns = [
                r'https://auth\.tavily\.com/u/email-verification\?ticket=[^\s<>"\']+',
                r'https://[^\s<>"\']*tavily\.com[^\s<>"\']*verify[^\s<>"\']*',
                r'https://[^\s<>"\']*tavily\.com[^\s<>"\']*'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, page_content, re.IGNORECASE)
                if matches:
                    link = matches[0].rstrip('#')  # 移除末尾的#
                    print(f"✅ 从页面文本中提取到验证链接: {link}")
                    return link

            print("⚠️ 未找到验证链接")
            print(f"📄 页面内容预览: {page_content[:500]}...")
            return None

        except Exception as e:
            print(f"❌ 提取验证链接失败: {e}")
            return None

    def extract_link_from_text(self, text):
        """从文本中提取验证链接"""
        try:
            # 使用正则表达式查找Tavily验证链接
            patterns = [
                r'https://auth\.tavily\.com/u/email-verification\?ticket=[^\s<>"\'#]+',
                r'https://[^\s<>"\']*tavily[^\s<>"\']*verify[^\s<>"\']*',
                r'https://[^\s<>"\']*verify[^\s<>"\']*tavily[^\s<>"\']*',
                r'https://auth\.tavily\.com[^\s<>"\']*'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    # 返回第一个匹配的链接
                    link = matches[0].rstrip('#')  # 移除末尾的#
                    return link

            return None

        except Exception as e:
            print(f"❌ 从文本提取链接失败: {e}")
            return None

    def navigate_to_verification_link(self, verification_link):
        """导航到验证链接并处理弹窗"""
        try:
            print(f"🔗 正在访问验证链接: {verification_link}")

            # 设置页面事件监听
            popup_handled = False

            def handle_popup(dialog):
                nonlocal popup_handled
                try:
                    print(f"🔔 检测到弹窗: {dialog.message}")
                    if "第三方网站跳转提醒" in dialog.message or "即将离开" in dialog.message or "继续前往" in dialog.message:
                        print("✅ 确认跳转到验证页面")
                        dialog.accept()
                        popup_handled = True
                    else:
                        print("❌ 取消弹窗")
                        dialog.dismiss()
                except Exception as e:
                    print(f"⚠️ 处理弹窗失败: {e}")
                    try:
                        dialog.dismiss()
                    except:
                        pass

            # 监听弹窗
            self.page.on("dialog", handle_popup)

            # 访问验证链接
            self.page.goto(verification_link)
            wait_with_message(5, "等待验证页面加载")

            # 检查是否成功跳转到验证页面
            current_url = self.page.url
            if "tavily.com" in current_url:
                print(f"✅ 成功跳转到Tavily页面: {current_url}")

                # 检查是否是登录页面
                if "login" in current_url.lower():
                    print("🔑 检测到Tavily登录页面，需要进行登录")
                    return "login_required"
                else:
                    print("✅ 邮箱验证可能已完成")
                    return True
            else:
                print(f"⚠️ 当前页面: {current_url}")
                print("可能需要手动处理验证")
                return False

        except Exception as e:
            print(f"❌ 访问验证链接失败: {e}")
            return False

    def login_to_tavily(self, email, password):
        """登录到Tavily账户（支持分步登录）"""
        try:
            print(f"🔑 开始登录Tavily账户: {email}")

            # 等待登录页面加载
            wait_with_message(3, "等待登录页面加载")

            # 步骤1: 输入邮箱
            if not self._input_email_step(email):
                return False

            # 步骤2: 点击继续按钮（如果存在）
            if not self._click_continue_if_exists():
                print("⚠️ 未找到继续按钮，可能是单页登录")

            # 步骤3: 输入密码
            if not self._input_password_step(password):
                return False

            # 步骤4: 提交登录
            if not self._submit_login():
                return False

            # 步骤5: 验证登录结果
            return self._verify_login_success()

        except Exception as e:
            print(f"❌ 登录Tavily失败: {e}")
            return False

    def _input_email_step(self, email):
        """输入邮箱步骤"""
        email_selectors = [
            'input[name="username"]',  # Tavily使用username字段
            'input[type="email"]',
            'input[name="email"]',
            'input[placeholder*="email"]',
            'input[placeholder*="Email"]',
            '#email',
            '#username',
            '.email-input'
        ]

        email_input = None
        for selector in email_selectors:
            try:
                email_input = self.page.wait_for_selector(selector, timeout=5000)
                if email_input:
                    print(f"✅ 找到邮箱输入框: {selector}")
                    break
            except:
                continue

        if not email_input:
            print("❌ 未找到邮箱输入框")
            return False

        # 输入邮箱
        email_input.fill(email)
        print(f"✅ 已输入邮箱: {email}")
        wait_with_message(1, "等待输入完成")
        return True

    def _click_continue_if_exists(self):
        """点击继续按钮（如果存在）"""
        continue_selectors = [
            'button[type="submit"]:has-text("Continue")',
            'button:has-text("Continue")',
            'button:has-text("Next")',
            'button[name="action"][type="submit"]',
            'button[type="submit"]'
        ]

        for selector in continue_selectors:
            try:
                continue_button = self.page.wait_for_selector(selector, timeout=3000)
                if continue_button:
                    print(f"✅ 找到继续按钮: {selector}")
                    continue_button.click()
                    wait_with_message(3, "等待页面跳转")
                    return True
            except:
                continue

        return False

    def _input_password_step(self, password):
        """输入密码步骤"""
        # 等待密码页面加载
        wait_with_message(2, "等待密码页面加载")

        password_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            'input[placeholder*="password"]',
            'input[placeholder*="Password"]',
            '#password',
            '.password-input'
        ]

        password_input = None
        for selector in password_selectors:
            try:
                password_input = self.page.wait_for_selector(selector, timeout=5000)
                if password_input:
                    print(f"✅ 找到密码输入框: {selector}")
                    break
            except:
                continue

        if not password_input:
            print("❌ 未找到密码输入框")
            return False

        # 输入密码
        password_input.fill(password)
        print("✅ 已输入密码")
        wait_with_message(1, "等待输入完成")
        return True

    def _submit_login(self):
        """提交登录"""
        login_selectors = [
            'button[type="submit"]:has-text("Continue")',
            'button[type="submit"]:has-text("Log in")',
            'button:has-text("Log in")',
            'button:has-text("Login")',
            'button:has-text("Sign in")',
            'button[name="action"][type="submit"]',
            'button[type="submit"]',
            'input[type="submit"]',
            '.login-btn',
            '.submit-btn'
        ]

        login_button = None
        for selector in login_selectors:
            try:
                login_button = self.page.wait_for_selector(selector, timeout=5000)
                if login_button:
                    print(f"✅ 找到登录按钮: {selector}")
                    break
            except:
                continue

        if login_button:
            print("🔑 正在点击登录按钮...")
            login_button.click()
        else:
            print("⚠️ 未找到登录按钮，尝试按Enter键...")
            # 尝试在密码框按Enter
            password_inputs = self.page.query_selector_all('input[type="password"]')
            if password_inputs:
                password_inputs[0].press('Enter')
            else:
                return False

        # 等待登录完成
        wait_with_message(5, "等待登录完成")
        return True

    def _verify_login_success(self):
        """验证登录是否成功"""
        current_url = self.page.url
        print(f"📋 登录后页面: {current_url}")

        # 检查是否成功登录
        if any(keyword in current_url.lower() for keyword in ['dashboard', 'home', 'app', 'console']):
            print("✅ 登录成功!")
            return True
        elif "login" in current_url.lower():
            print("❌ 登录失败，仍在登录页面")
            return False
        else:
            print("✅ 登录可能成功，已跳转到新页面")
            return True

    def get_api_key_from_tavily(self):
        """从Tavily获取API key"""
        try:
            print("🔑 开始查找API key...")

            # 等待页面完全加载
            wait_with_message(2, "等待页面加载")

            current_url = self.page.url
            print(f"📋 当前页面: {current_url}")

            # 如果不在home页面，先导航到home页面
            if "app.tavily.com/home" not in current_url:
                home_url = "https://app.tavily.com/home"
                print(f"🏠 导航到home页面: {home_url}")
                self.page.goto(home_url)
                wait_with_message(2, "等待home页面加载")

            # 步骤1: 先尝试点击眼睛图标显示完整API key
            print("👁️ 查找并点击眼睛图标显示完整API key...")
            if self.click_eye_icon_to_show_api_key():
                print("✅ 成功点击眼睛图标，API key应该已显示")
                wait_with_message(1, "等待API key显示")
            else:
                print("⚠️ 未找到眼睛图标，API key可能已经显示")

            # 步骤2: 在home页面查找API key
            print("🔍 在home页面查找API key...")
            api_key = self.find_api_key_on_page()
            if api_key and not '*' in api_key:
                return api_key

            # 查找复制按钮（根据用户提供的HTML结构）
            print("🔍 查找复制按钮...")
            copy_buttons = self.page.query_selector_all('button.chakra-button.css-1nit5dt')

            for i, button in enumerate(copy_buttons):
                try:
                    # 检查按钮是否包含复制图标的SVG
                    svg = button.query_selector('svg')
                    if svg:
                        # 检查SVG是否包含复制图标的路径
                        rect = svg.query_selector('rect[x="9"][y="9"]')
                        path = svg.query_selector('path[d*="M5 15H4a2 2 0 0 1-2-2V4"]')

                        if rect and path:
                            print(f"✅ 找到复制按钮 {i+1}")

                            # 查找复制按钮附近的API key
                            parent = button.evaluate('el => el.parentElement')
                            if parent:
                                # 在父元素中查找API key
                                parent_text = button.evaluate('el => el.parentElement.innerText')
                                if parent_text and 'tvly-' in parent_text:
                                    import re
                                    match = re.search(r'tvly-[a-zA-Z0-9_-]+', parent_text)
                                    if match:
                                        api_key = match.group(0)
                                        print(f"✅ 从复制按钮附近找到API key: {api_key}")
                                        return api_key

                            # 尝试点击复制按钮
                            print("🔗 尝试点击复制按钮...")
                            button.click()
                            wait_with_message(1, "等待复制完成")

                            # 尝试从剪贴板获取（如果支持）
                            try:
                                clipboard_text = self.page.evaluate('() => navigator.clipboard.readText()')
                                if clipboard_text and 'tvly-' in clipboard_text:
                                    print(f"✅ 从剪贴板获取API key: {clipboard_text}")
                                    return clipboard_text.strip()
                            except:
                                print("⚠️ 无法从剪贴板读取")

                except Exception as e:
                    print(f"⚠️ 处理复制按钮 {i+1} 失败: {e}")
                    continue

            print("❌ 未找到API key")
            return None

        except Exception as e:
            print(f"❌ 获取API key失败: {e}")
            return None

    def click_eye_icon_to_show_api_key(self):
        """点击眼睛图标显示完整的API key（多种策略）"""
        try:
            print("👁️ 开始多策略眼睛图标点击流程...")

            # 策略1: 先系统性处理弹窗，再点击眼睛
            print("🎭 策略1: 系统性处理弹窗后点击眼睛")
            try:
                self.close_all_popups_systematically()
                # 稳定弹窗处理完成后，等待页面完全稳定
                wait_with_message(1, "等待页面完全稳定")

                if self._try_click_eye_icon():
                    print("✅ 策略1成功：稳定弹窗处理后眼睛点击成功")
                    return True
            except Exception as e:
                print(f"⚠️ 策略1失败: {e}")

            # 策略2: 忽略弹窗，直接尝试点击眼睛（多种方法）
            print("🎯 策略2: 忽略弹窗直接点击眼睛")
            for attempt in range(3):
                try:
                    print(f"  尝试 {attempt + 1}/3: 直接点击眼睛图标")
                    if self._try_click_eye_icon_force():
                        print("✅ 策略2成功：强制点击眼睛成功")
                        return True
                    wait_with_message(1, "等待页面响应")
                except Exception as e:
                    print(f"  尝试 {attempt + 1} 失败: {e}")

            # 策略3: 滚动页面后再尝试
            print("📜 策略3: 滚动页面后点击眼睛")
            try:
                self._scroll_and_click_eye()
                print("✅ 策略3成功：滚动后眼睛点击成功")
                return True
            except Exception as e:
                print(f"⚠️ 策略3失败: {e}")

            # 策略4: 使用键盘操作
            print("⌨️ 策略4: 使用键盘操作")
            try:
                self._keyboard_navigate_to_eye()
                print("✅ 策略4成功：键盘操作成功")
                return True
            except Exception as e:
                print(f"⚠️ 策略4失败: {e}")

            print("❌ 所有策略都失败了")
            return False

        except Exception as e:
            print(f"❌ 眼睛图标点击完全失败: {e}")
            return False

    def _try_click_eye_icon(self):
        """尝试点击眼睛图标（常规方法）"""
        eye_button_selectors = [
            'button.chakra-button.css-1a1nl3a',
            'button[type="button"]:has(svg[viewBox="0 0 24 24"])',
            'button:has(svg path[d*="M12 6.5"])',
            'button[aria-label*="show" i]',
            'button[aria-label*="reveal" i]'
        ]

        for selector in eye_button_selectors:
            try:
                print(f"🔍 尝试眼睛图标选择器: {selector}")
                eye_buttons = self.page.query_selector_all(selector)

                for i, button in enumerate(eye_buttons):
                    try:
                        print(f"✅ 找到眼睛图标按钮 {i+1}")
                        button.click()
                        print("👁️ 已点击眼睛图标")
                        return True
                    except Exception as e:
                        print(f"⚠️ 检查眼睛按钮 {i+1} 失败: {e}")
                        continue

            except Exception as e:
                print(f"⚠️ 选择器 {selector} 失败: {e}")
                continue

        return False

    def _try_click_eye_icon_force(self):
        """强制尝试点击眼睛图标（忽略弹窗）"""
        try:
            # 查找所有可能的眼睛图标按钮
            all_buttons = self.page.query_selector_all('button')

            for i, button in enumerate(all_buttons):
                try:
                    # 检查按钮的HTML内容是否包含眼睛图标特征
                    button_html = button.inner_html()
                    if ('viewBox="0 0 24 24"' in button_html and
                        ('M12 6.5' in button_html or 'eye' in button_html.lower())):
                        print(f"✅ 找到可能的眼睛图标按钮 {i+1}")

                        # 强制点击，忽略可能的遮挡
                        button.click(force=True)
                        print("👁️ 已强制点击眼睛图标")
                        return True

                except Exception as e:
                    continue

            return False

        except Exception as e:
            print(f"❌ 强制点击眼睛图标失败: {e}")
            return False

    def _scroll_and_click_eye(self):
        """滚动页面后点击眼睛图标"""
        try:
            print("📜 滚动页面寻找眼睛图标...")

            # 滚动到页面顶部
            self.page.evaluate("window.scrollTo(0, 0)")
            wait_with_message(1, "等待滚动完成")

            # 尝试点击眼睛图标
            if self._try_click_eye_icon():
                return True

            # 滚动到页面中部
            self.page.evaluate("window.scrollTo(0, window.innerHeight / 2)")
            wait_with_message(1, "等待滚动完成")

            # 再次尝试点击眼睛图标
            if self._try_click_eye_icon():
                return True

            return False

        except Exception as e:
            print(f"❌ 滚动点击失败: {e}")
            return False

    def _keyboard_navigate_to_eye(self):
        """使用键盘导航到眼睛图标"""
        try:
            print("⌨️ 使用键盘导航...")

            # 按Tab键导航到可能的眼睛图标
            for i in range(10):  # 最多按10次Tab
                self.page.keyboard.press('Tab')
                wait_with_message(0.5, f"Tab导航 {i+1}/10")

                # 检查当前焦点元素是否是眼睛图标
                focused_element = self.page.evaluate("document.activeElement")
                if focused_element:
                    # 按Enter尝试激活
                    self.page.keyboard.press('Enter')
                    wait_with_message(1, "等待响应")

                    # 检查是否成功显示了API key
                    if self._check_api_key_visible():
                        print("✅ 键盘导航成功")
                        return True

            return False

        except Exception as e:
            print(f"❌ 键盘导航失败: {e}")
            return False

    def _check_api_key_visible(self):
        """检查API key是否已显示"""
        try:
            # 查找可能包含完整API key的元素
            api_key_selectors = [
                'input[value*="tvly-"]',
                'span:has-text("tvly-")',
                'div:has-text("tvly-")',
                'code:has-text("tvly-")'
            ]

            for selector in api_key_selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element:
                        text = element.inner_text() or element.input_value() or ''
                        if text.startswith('tvly-') and len(text) > 30:
                            return True
                except:
                    continue

            return False

        except:
            return False

    def close_all_popups_systematically(self):
        """系统性地关闭所有弹窗（稳定版：1秒间隔点击）"""
        try:
            print("🎭 开始稳定弹窗处理流程...")

            # 第一步：点击Get Started
            if self._click_get_started():
                print("✅ 成功点击Get Started")
                # 添加1秒延迟
                time.sleep(1.0)
            else:
                print("⚠️ 未找到Get Started按钮")
                return False

            # 第二步：连续点击Next按钮（1秒间隔）
            next_clicks = 0
            max_next_clicks = 4  # 明确设置为4次

            print("🚀 开始连续点击Next按钮（1秒间隔）...")
            while next_clicks < max_next_clicks:
                if self._click_next_button():
                    next_clicks += 1
                    print(f"✅ 成功点击第{next_clicks}个Next按钮")
                    # 添加1秒延迟，让页面有充足时间响应
                    if next_clicks < max_next_clicks:  # 最后一次点击后不需要延迟
                        time.sleep(1.0)
                else:
                    print(f"⚠️ 未找到更多Next按钮，已点击{next_clicks}个")
                    break

            # 第三步：点击关闭按钮（1秒延迟后）
            time.sleep(1.0)  # 在点击关闭按钮前稍作延迟
            print("🔚 点击关闭按钮...")
            if self._click_close_button():
                print("✅ 成功点击关闭按钮")
            else:
                print("⚠️ 未找到关闭按钮，尝试其他方法")
                self._try_other_close_methods()

            print(f"🎭 稳定弹窗处理完成，共点击了{next_clicks}个Next按钮")
            return True

        except Exception as e:
            print(f"❌ 稳定弹窗处理失败: {e}")
            return False

    def _click_get_started(self):
        """点击Get Started按钮"""
        get_started_selectors = [
            'button:has-text("Get Started")',
            'button:contains("Get Started")',
            '[role="button"]:has-text("Get Started")',
            'button[type="button"]:has-text("Get Started")',
            '.chakra-button:has-text("Get Started")'
        ]

        for selector in get_started_selectors:
            try:
                btn = self.page.query_selector(selector)
                if btn:
                    print(f"✅ 找到Get Started按钮: {selector}")
                    btn.click()
                    return True
            except:
                continue
        return False

    def _click_next_button(self):
        """点击Next按钮"""
        next_selectors = [
            'button:has-text("Next")',
            'button:contains("Next")',
            '[role="button"]:has-text("Next")',
            'button[type="button"]:has-text("Next")',
            '.chakra-button:has-text("Next")',
            'button:has-text("Continue")',
            'button:has-text("Skip")',
            'button:has-text("Got it")',
            'button:has-text("OK")'
        ]

        for selector in next_selectors:
            try:
                btn = self.page.query_selector(selector)
                if btn:
                    print(f"✅ 找到Next/Continue按钮: {selector}")
                    btn.click()
                    return True
            except:
                continue
        return False

    def _click_close_button(self):
        """点击关闭按钮"""
        close_selectors = [
            'button[aria-label="Close"]',
            'button[aria-label="close"]',
            'button:has-text("Close")',
            'button:has-text("×")',
            'button.close',
            '.close-button',
            '[data-testid="close"]',
            '[data-testid="close-button"]'
        ]

        for selector in close_selectors:
            try:
                btn = self.page.query_selector(selector)
                if btn:
                    print(f"✅ 找到关闭按钮: {selector}")
                    btn.click()
                    return True
            except:
                continue
        return False

    def _try_other_close_methods(self):
        """尝试其他关闭方法"""
        try:
            # 方法1: 查找关闭按钮
            close_button_selectors = [
                'button[aria-label="Close"]',
                'button[aria-label="close"]',
                'button.close',
                '.close-button',
                '[data-testid="close"]',
                '[data-testid="close-button"]',
                'button:has(svg[data-icon="times"])',
                'button:has(svg[data-icon="close"])',
                '.modal-close',
                '.popup-close'
            ]

            for selector in close_button_selectors:
                try:
                    close_buttons = self.page.query_selector_all(selector)
                    if close_buttons:
                        print(f"✅ 找到关闭按钮: {selector}")
                        close_buttons[0].click()
                        wait_with_message(1, "等待弹窗关闭")
                        return True
                except:
                    continue

            # 方法2: 查找遮罩层并点击
            overlay_selectors = [
                '.overlay',
                '.modal-overlay',
                '.backdrop',
                '.popup-overlay',
                '[data-testid="overlay"]'
            ]

            for selector in overlay_selectors:
                try:
                    overlays = self.page.query_selector_all(selector)
                    if overlays:
                        print(f"✅ 找到遮罩层: {selector}")
                        overlays[0].click()
                        wait_with_message(1, "等待弹窗关闭")
                        return True
                except:
                    continue

            # 方法3: 点击页面空白区域关闭弹窗
            print("🔍 尝试点击页面空白区域关闭弹窗...")
            try:
                # 点击页面左上角空白区域
                self.page.click('body', position={'x': 50, 'y': 50})
                wait_with_message(1, "等待弹窗关闭")
                print("✅ 已点击页面空白区域")
                return True
            except:
                pass

            # 方法4: 按ESC键关闭弹窗
            print("🔍 尝试按ESC键关闭弹窗...")
            try:
                self.page.keyboard.press('Escape')
                wait_with_message(1, "等待弹窗关闭")
                print("✅ 已按ESC键")
                return True
            except:
                pass

            print("⚠️ 未检测到悬浮弹窗或无法关闭")
            return False

        except Exception as e:
            print(f"⚠️ 关闭悬浮弹窗失败: {e}")
            return False

    def find_api_key_on_page(self):
        """在当前页面查找API key"""
        try:
            # 查找包含API key的元素
            api_key_selectors = [
                'input[value*="tvly-"]',
                'code:has-text("tvly-")',
                'span:has-text("tvly-")',
                'div:has-text("tvly-")',
                '.api-key',
                '[data-testid*="api"]',
                'input[readonly]',
                '.token',
                '.key-value'
            ]

            for selector in api_key_selectors:
                try:
                    elements = self.page.query_selector_all(selector)
                    for element in elements:
                        # 尝试从value属性获取
                        value = element.get_attribute('value') or ''
                        if 'tvly-' in value:
                            print(f"✅ 从input value中找到API key: {value}")
                            return value.strip()

                        # 尝试从文本内容获取
                        text = element.inner_text() or ''
                        if 'tvly-' in text:
                            # 使用正则表达式提取API key
                            import re
                            match = re.search(r'tvly-[a-zA-Z0-9_-]+', text)
                            if match:
                                api_key = match.group(0)
                                print(f"✅ 从文本中找到API key: {api_key}")
                                return api_key
                except:
                    continue

            # 如果没找到，尝试从页面所有文本中搜索
            page_content = self.page.inner_text('body')
            import re
            matches = re.findall(r'tvly-[a-zA-Z0-9_-]+', page_content)
            if matches:
                api_key = matches[0]
                print(f"✅ 从页面文本中找到API key: {api_key}")
                return api_key

            return None

        except Exception as e:
            print(f"❌ 在页面中查找API key失败: {e}")
            return None

    def wait_for_email(self, target_email, max_wait_time=300):
        """等待验证邮件到达"""
        print(f"⏳ 等待验证邮件，最长等待 {max_wait_time} 秒...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # 刷新页面
            try:
                self.page.reload()
                wait_with_message(3, "刷新页面")
                
                # 检查验证邮件
                verification_link = self.check_for_tavily_email(target_email)
                if verification_link:
                    return verification_link
                
                elapsed = int(time.time() - start_time)
                print(f"⏳ 未收到验证邮件，继续等待... ({elapsed}s)")
                
                # 等待30秒后再次检查
                wait_with_message(30, "等待新邮件")
                
            except Exception as e:
                print(f"⚠️ 检查邮件时出错: {e}")
                wait_with_message(10, "等待后重试")
        
        print("❌ 等待超时，未收到验证邮件")
        return None


def main():
    """主函数 - 用于测试邮箱检查功能"""
    checker = EmailChecker()
    
    try:
        checker.start_browser()
        
        if not checker.load_email_page():
            print("❌ 无法加载邮箱页面，请先运行 email_login_helper.py 进行登录设置")
            return
        
        # 测试查找邮件功能
        print("\n🧪 测试查找邮件功能...")
        emails = checker.find_emails_on_page()
        
        if emails:
            print(f"✅ 找到 {len(emails)} 个邮件")
            for i, email in enumerate(emails[:5]):  # 显示前5个
                print(f"  {i+1}. {email['text'][:100]}...")
        else:
            print("⚠️ 未找到任何邮件")
        
        # 询问是否要等待验证邮件
        test_email = input("\n输入要测试的邮箱地址（或按Enter跳过）: ").strip()
        if test_email:
            verification_link = checker.wait_for_email(test_email, 60)  # 等待1分钟
            if verification_link:
                print(f"🎉 成功获取验证链接: {verification_link}")
            else:
                print("❌ 未能获取验证链接")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断了程序")
    except Exception as e:
        print(f"\n❌ 程序出错: {e}")
    finally:
        checker.close_browser()


if __name__ == "__main__":
    main()
