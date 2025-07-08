import os
import pandas as pd
from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ConversationHandler, ContextTypes
)

BOT_TOKEN ='7831163997:AAGCps4bfKRpS4Nvb9KxffoEMvTJFCbCtRA'
ADMIN_IDS = [818577888]  # لیست ادمین‌ها
CARD_NUMBER = "1111 2222 3333 4444"
MAX_USERS = 1000

# مسیر فایل ذخیره داده‌ها
DATA_FILE = "lottery_data.xlsx"
OVERFLOW_FILE = "overflow_users.xlsx"
COUNTER_FILE = "counter.txt"

# مراحل گفتگو
(GET_INFO, FULLNAME, CONFIRM, AGREE, RECEIPT, WAIT_ADMIN) = range(6)

# --- کمک‌تابع‌ها ---

def read_counter():
    if not os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "w") as f:
            f.write("0")
        return 0
    with open(COUNTER_FILE, "r") as f:
        return int(f.read())

def write_counter(val):
    with open(COUNTER_FILE, "w") as f:
        f.write(str(val))

def save_user(data):
    # بررسی ظرفیت
    if os.path.exists(DATA_FILE):
        df = pd.read_excel(DATA_FILE)
    else:
        df = pd.DataFrame(columns=["user_id","fullname","phone","card_used","card_owner","receipt_file","code"])

    if len(df) >= MAX_USERS:
        # ذخیره در overflow
        if os.path.exists(OVERFLOW_FILE):
            overflow_df = pd.read_excel(OVERFLOW_FILE)
        else:
            overflow_df = pd.DataFrame(columns=df.columns)
        overflow_df = pd.concat([overflow_df, pd.DataFrame([data])], ignore_index=True)
        overflow_df.to_excel(OVERFLOW_FILE, index=False)
        return False

    df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
    df.to_excel(DATA_FILE, index=False)
    return True

# --- شروع گفتگو ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎉 به ربات قرعه‌کشی خوش آمدید!\n\n"
        "لطفاً شماره موبایل 11 رقمی خود را بدون صفر اول ارسال کنید:"
    )
    return GET_INFO

async def get_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if 'phone' not in context.user_data:
        # دریافت شماره موبایل
        phone = text
        if len(phone) == 11 and phone.isdigit():
            # حذف صفر اول و اضافه کردن +98
            if phone.startswith("0"):
                phone = "+98" + phone[1:]
            else:
                phone = "+98" + phone
            context.user_data['phone'] = phone
            await update.message.reply_text("شماره موبایل ثبت شد.\nلطفاً شماره کارت 16 رقمی خود را بدون فاصله ارسال کنید:")
            return GET_INFO
        else:
            await update.message.reply_text("شماره موبایل باید 11 رقمی و فقط عدد باشد. دوباره ارسال کنید:")
            return GET_INFO

    elif 'card_used' not in context.user_data:
        # دریافت شماره کارت و اعتبارسنجی
        card = text.replace(" ", "")
        if card.isdigit() and len(card) == 16:
            context.user_data['card_used'] = card
            await update.message.reply_text("شماره کارت ثبت شد.\nلطفاً نام و نام خانوادگی خود را ارسال کنید:")
            return FULLNAME
        else:
            await update.message.reply_text("شماره کارت باید 16 رقم و فقط شامل عدد باشد. دوباره ارسال کنید:")
            return GET_INFO

async def fullname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['fullname'] = update.message.text.strip()

    # نمایش خلاصه اطلاعات و درخواست تایید
    phone = context.user_data['phone']
    card = context.user_data['card_used']
    fullname = context.user_data['fullname']

    summary = (
        f"لطفا اطلاعات وارد شده را بررسی کنید:\n\n"
        f"📱 شماره موبایل: {phone}\n"
        f"💳 شماره کارت: {card}\n"
        f"🧑‍💼 نام و نام خانوادگی: {fullname}\n\n"
        "اگر اطلاعات درست است، لطفا «تایید» را ارسال کنید.\n"
        "در غیر این صورت «اصلاح» را ارسال کنید."
    )
    keyboard = [['تایید', 'اصلاح']]
    await update.message.reply_text(summary,
                                    reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
    return CONFIRM

async def confirm_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "تایید":
        await update.message.reply_text(
            f"💳 لطفاً مبلغ را به شماره کارت زیر واریز کنید:\n\n{CARD_NUMBER}\n\n"
            "پس از واریز، عکس فیش را ارسال کنید.",
            reply_markup=ReplyKeyboardRemove()
        )
        return RECEIPT
    elif text == "اصلاح":
        context.user_data.clear()
        await update.message.reply_text("لطفا دوباره شماره موبایل 11 رقمی خود را بدون صفر اول ارسال کنید:")
        return GET_INFO
    else:
        await update.message.reply_text("لطفا فقط «تایید» یا «اصلاح» ارسال کنید.")
        return CONFIRM

async def receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("لطفا فقط عکس فیش واریز را ارسال کنید.")
        return RECEIPT

    # ذخیره عکس فیش
    photo_file = await update.message.photo[-1].get_file()
    file_path = f"receipts/{update.message.from_user.id}.jpg"
    os.makedirs("receipts", exist_ok=True)
    await photo_file.download_to_drive(file_path)

    context.user_data['receipt_file'] = file_path

    # ظرفیت بررسی
    current_count = 0
    if os.path.exists(DATA_FILE):
        df = pd.read_excel(DATA_FILE)
        current_count = len(df)

    if current_count >= MAX_USERS:
        # ذخیره در overflow
        overflow = pd.DataFrame([{
            "user_id": update.message.from_user.id,
            "fullname": context.user_data['fullname'],
            "phone": context.user_data['phone'],
            "card_used": context.user_data['card_used'],
            "card_owner": context.user_data.get('card_owner', ''),
            "receipt_file": file_path,
            "code": ""
        }])
        if os.path.exists(OVERFLOW_FILE):
            overflow_df = pd.read_excel(OVERFLOW_FILE)
            overflow_df = pd.concat([overflow_df, overflow], ignore_index=True)
        else:
            overflow_df = overflow
        overflow_df.to_excel(OVERFLOW_FILE, index=False)
        await update.message.reply_text("ظرفیت قرعه‌کشی تکمیل شده است. با تشکر از همکاری شما.")
        # اطلاع ادمین‌ها
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, f"کاربر {update.message.from_user.id} پرداخت کرده ولی ظرفیت تکمیل است.")
            except:
                pass
        return ConversationHandler.END

    # ذخیره موقت کارت صاحب پول (در اینجا می‌توان درخواست کرد یا بعدا)
    await update.message.reply_text("لطفا نام و نام خانوادگی صاحب شماره کارت واریزی را ارسال کنید:")
    return WAIT_ADMIN

async def card_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['card_owner'] = update.message.text.strip()

    # ثبت اطلاعات موقت و ارسال به ادمین برای تایید
    code = read_counter() + 1
    write_counter(code)

    data_to_save = {
        "user_id": update.message.from_user.id,
        "fullname": context.user_data['fullname'],
        "phone": context.user_data['phone'],
        "card_used": context.user_data['card_used'],
        "card_owner": context.user_data['card_owner'],
        "receipt_file": context.user_data['receipt_file'],
        "code": f"{code:03d}"
    }

    success = save_user(data_to_save)

    if not success:
        await update.message.reply_text("ظرفیت تکمیل شده است و ثبت شما در صف انتظار قرار گرفت.")
        return ConversationHandler.END

    # ارسال اطلاعات به ادمین‌ها
    msg_admin = (
        f"✅ کاربر جدید ثبت شد:\n\n"
        f"👤 نام: {data_to_save['fullname']}\n"
        f"📱 موبایل: {data_to_save['phone']}\n"
        f"💳 کارت واریز: {data_to_save['card_used']}\n"
        f"👤 صاحب کارت: {data_to_save['card_owner']}\n"
        f"🎟️ کد قرعه‌کشی: {data_to_save['code']}\n"
        f"📸 عکس فیش در پوشه receipts موجود است."
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, msg_admin)
        except:
            pass

    # پیام موفقیت به کاربر
    await update.message.reply_text(
        f"ثبت شما با موفقیت انجام شد.\n"
        f"کد قرعه‌کشی شما: {data_to_save['code']}\n"
        "پس از تایید ادمین کد نهایی برای شما ارسال خواهد شد."
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات لغو شد.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

# --- تنظیم ConversationHandler ---

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        GET_INFO: [MessageHandler(filters.TEXT & (~filters.COMMAND), get_info)],
        FULLNAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), fullname)],
        CONFIRM: [MessageHandler(filters.Regex("^(تایید|اصلاح)$"), confirm_info)],
        AGREE: [MessageHandler(filters.Regex("^(بله|خیر)$"), lambda u,c: None)],  # در این کد فعلا استفاده نمی‌شود
        RECEIPT: [MessageHandler(filters.PHOTO, receipt)],
        WAIT_ADMIN: [MessageHandler(filters.TEXT & (~filters.COMMAND), card_owner)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# --- راه‌اندازی ربات ---

import asyncio
import nest_asyncio

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(conv)

    print("🤖 ربات فعال است و منتظر پیام‌هاست...")

    await app.run_polling(
        poll_interval=5,
        timeout=30
    )

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
