import os
import re

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PostbackAction,
    QuickReply,
    QuickReplyItem,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import (
    MessageEvent,
    PostbackEvent,
    TextMessageContent,
)


# =========================================================
# 1. โหลดค่าจาก .env
# =========================================================

load_dotenv()

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

if not CHANNEL_SECRET:
    raise RuntimeError(
        "ไม่พบ LINE_CHANNEL_SECRET ในไฟล์ .env"
    )

if not CHANNEL_ACCESS_TOKEN:
    raise RuntimeError(
        "ไม่พบ LINE_CHANNEL_ACCESS_TOKEN ในไฟล์ .env"
    )


# =========================================================
# 2. ตั้งค่าข้อมูล Tata Assistant
# =========================================================

MS_FORM_URL = (
    "https://forms.cloud.microsoft/r/xbeh7kJip9"
)

FOCUS_PRODUCT_URL = (
    "https://drive.google.com/drive/folders/"
    "1QaDJWCB1h0XOyXX8VNNXA7UgnsNPxtg7"
    "?usp=drive_link"
)

DASHBOARD_URL = (
    "https://cpallgroup-my.sharepoint.com/:x:/r/"
    "personal/savapatple_cpall_co_th/_layouts/15/"
    "Doc.aspx?sourcedoc=%7BF618A060-A5E2-4517-AFAF-"
    "369174C33465%7D&file=%E0%B9%81%E0%B8%9A%E0%B8%9A"
    "%E0%B8%9F%E0%B8%AD%E0%B8%A3%E0%B9%8C%E0%B8%A1"
    "%E0%B8%95%E0%B8%B4%E0%B8%94%E0%B8%95%E0%B8%B2"
    "%E0%B8%A1_%E0%B8%A2%E0%B8%AD%E0%B8%94%E0%B8%82"
    "%E0%B8%B2%E0%B8%A2%E0%B9%82%E0%B8%84%E0%B8%A3"
    "%E0%B8%87%E0%B8%81%E0%B8%B2%E0%B8%A3%E0%B8%9E"
    "%E0%B8%B1%E0%B8%92%E0%B8%99%E0%B8%B2%E0%B8%9C"
    "%E0%B8%B9%E0%B9%89%E0%B8%8A%E0%B9%88%E0%B8%A7"
    "%E0%B8%A2%E0%B9%80%E0%B8%A0%E0%B8%AA%E0%B8%B1"
    "%E0%B8%8A%E0%B8%81%E0%B8%A3.xlsx"
    "&action=edit&mobileredirect=true"
)

MANUAL_URL = (
    "https://drive.google.com/drive/folders/"
    "10b6oFc3g5p516EebmGrSSUKG2K7b9O4P"
    "?usp=sharing"
)

ADMINS = [
    {
        "name": "มด",
        "phone": "093-398-9851",
        "role": "PLP เพื่อนสุขภาพ",
    },
    {
        "name": "โอปอล์",
        "phone": "081-555-8565",
        "role": "PLP เพื่อนสุขภาพ",
    },
    {
        "name": "แนน",
        "phone": "06-3561-6215",
        "role": "PLP เพื่อนสุขภาพ",
    },
]

LATEST_NEWS = """
📢 ข่าวสารล่าสุด

• กรุณาส่งยอดขายตามรอบเวลาที่กำหนด
• ตรวจสอบสินค้า Focus ก่อนเสนอขาย
• หากพบปัญหา ติดต่อ Admin กลุ่ม
""".strip()


# =========================================================
# 3. สร้าง FastAPI และ LINE SDK
# =========================================================

app = FastAPI(title="Tata Assistant")

configuration = Configuration(
    access_token=CHANNEL_ACCESS_TOKEN
)

handler = WebhookHandler(CHANNEL_SECRET)


# =========================================================
# 4. หน้าเช็กสถานะ Server
# =========================================================

@app.get("/")
def home() -> dict[str, str]:
    return {
        "status": "Tata Assistant Running",
        "message": "LINE webhook is ready",
    }


# =========================================================
# 5. รับ Webhook จาก LINE
# =========================================================

@app.post("/webhook")
async def webhook(
    request: Request,
) -> dict[str, str]:

    signature = request.headers.get(
        "x-line-signature"
    )

    body = await request.body()

    if not signature:
        raise HTTPException(
            status_code=400,
            detail="Missing X-Line-Signature",
        )

    try:
        handler.handle(
            body.decode("utf-8"),
            signature,
        )

    except InvalidSignatureError:
        raise HTTPException(
            status_code=400,
            detail="Invalid LINE signature",
        )

    except Exception as error:
        print(
            "Webhook error:",
            repr(error),
        )

        raise HTTPException(
            status_code=500,
            detail="Webhook processing failed",
        )

    return {"status": "OK"}


# =========================================================
# 6. ฟังก์ชันช่วยจัดข้อความ
# =========================================================

def normalize_text(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)

    return text


def is_tata_wake_word(text: str) -> bool:
    """
    คำที่ใช้เรียก Tata ให้เปิดเมนู

    ใช้การเทียบทั้งข้อความ
    เพื่อป้องกัน Tata แทรกบทสนทนาทั่วไป
    """

    normalized = normalize_text(text)

    wake_words = {
        "tata",
        "ตาต้า",
        "@tata",
        "@ตาต้า",
        "เรียก tata",
        "เรียกตาต้า",
        "เปิด tata",
        "เปิดตาต้า",
        "เมนู tata",
        "เมนูตาต้า",
    }

    return normalized in wake_words


# =========================================================
# 7. สร้างปุ่มเมนู Quick Reply
# =========================================================

def build_main_menu() -> QuickReply:
    return QuickReply(
        items=[
            QuickReplyItem(
                action=PostbackAction(
                    label="📋 ส่งยอด",
                    data="menu=sales_form",
                    display_text="📋 ส่งยอด",
                )
            ),
            QuickReplyItem(
                action=PostbackAction(
                    label="🎯 สินค้า Focus",
                    data="menu=focus",
                    display_text="🎯 สินค้า Focus",
                )
            ),
            # QuickReplyItem(
            #     action=PostbackAction(
            #         label="📊 Dashboard",
            #         data="menu=dashboard",
            #         display_text="📊 Dashboard",
            #     )
            # ),
            QuickReplyItem(
                action=PostbackAction(
                    label="📖 คู่มือการขาย",
                    data="menu=manual",
                    display_text="📖 คู่มือการขาย",
                )
            ),
            QuickReplyItem(
                action=PostbackAction(
                    label="📞 ติดต่อสอบถาม",
                    data="menu=contact",
                    display_text="📞 ติดต่อสอบถาม",
                )
            ),
            QuickReplyItem(
                action=PostbackAction(
                    label="📢 ข่าวสาร",
                    data="menu=news",
                    display_text="📢 ข่าวสาร",
                )
            ),
        ]
    )


# =========================================================
# 8. ข้อความแต่ละเมนู
# =========================================================

def welcome_message() -> str:
    return (
        "🤖 Tata Assistant\n\n"
        "สวัสดีค่ะ Tata พร้อมช่วยเหลือแล้ว\n"
        "กรุณาเลือกเมนูจากปุ่มด้านล่าง"
    )


def sales_form_message() -> str:
    return (
        "📋 แบบฟอร์มบันทึกยอดขายรายวัน\n\n"
        "กรุณากรอกข้อมูลผ่าน Microsoft Forms "
        "ตามรอบเวลาที่กำหนด\n\n"
        f"🔗 {MS_FORM_URL}\n\n"
        "กรุณาตรวจสอบรหัสสาขาและยอดขาย "
        "ก่อนกดส่งแบบฟอร์ม"
    )


def focus_product_message() -> str:
    return (
        "🎯 สินค้า Focus\n\n"
        "ตรวจสอบรายการสินค้า Focus "
        "และข้อมูลสำหรับเสนอขายได้ที่\n\n"
        f"🔗 {FOCUS_PRODUCT_URL}"
    )


def dashboard_message() -> str:
    return (
        "📊 Dashboard ติดตามยอดขาย\n\n"
        "ดูสถานะการส่งข้อมูล ยอดขายวันนี้ "
        "และยอดขายสะสมได้ที่\n\n"
        f"🔗 {DASHBOARD_URL}"
    )


def manual_message() -> str:
    return (
        "📖 คู่มือการทำงาน\n\n"
        "ดูวิธีส่งยอด แนวทางการเสนอขาย "
        "และขั้นตอนการปฏิบัติงานได้ที่\n\n"
        f"🔗 {MANUAL_URL}"
    )


def contact_message() -> str:
    admin_lines: list[str] = []

    for index, admin in enumerate(
        ADMINS,
        start=1,
    ):
        admin_lines.append(
            f"👤 Admin {index}: {admin['name']}\n"
            f"หน้าที่: {admin['role']}\n"
            f"เบอร์ติดต่อ: {admin['phone']}"
        )

    admin_text = "\n\n".join(admin_lines)

    return (
        "📞 ติดต่อสอบถาม\n\n"
        "กรณีพบปัญหาเกี่ยวกับแบบฟอร์ม "
        "Dashboard สินค้า Focus "
        "หรือการใช้งาน Tata Assistant "
        "สามารถติดต่อ Admin กลุ่มได้ดังนี้\n\n"
        f"{admin_text}"
    )


def news_message() -> str:
    return LATEST_NEWS


# =========================================================
# 9. ส่งข้อความตอบกลับ
# =========================================================

def reply_message(
    reply_token: str,
    text: str,
    show_menu: bool = False,
) -> None:

    quick_reply = (
        build_main_menu()
        if show_menu
        else None
    )

    message = TextMessage(
        text=text,
        quick_reply=quick_reply,
    )

    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)

        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[message],
            )
        )


# =========================================================
# 10. รับข้อความธรรมดา
# ตอบเฉพาะเมื่อเรียก Tata ก่อน
# =========================================================

@handler.add(
    MessageEvent,
    message=TextMessageContent,
)
def handle_text_message(
    event: MessageEvent,
) -> None:

    user_text = event.message.text.strip()

    print(
        "Received text:",
        user_text,
    )

    # ไม่ตอบข้อความทั่วไปในกลุ่ม
    if not is_tata_wake_word(user_text):
        return

    reply_message(
        reply_token=event.reply_token,
        text=welcome_message(),
        show_menu=True,
    )


# =========================================================
# 11. รับการกดปุ่มจาก Quick Reply
# =========================================================

@handler.add(PostbackEvent)
def handle_postback(
    event: PostbackEvent,
) -> None:

    postback_data = event.postback.data

    print(
        "Received postback:",
        postback_data,
    )

    menu_answers = {
        "menu=sales_form": sales_form_message,
        "menu=focus": focus_product_message,
        #"menu=dashboard": dashboard_message,
        "menu=manual": manual_message,
        "menu=contact": contact_message,
        "menu=news": news_message,
    }

    answer_function = menu_answers.get(
        postback_data
    )

    if answer_function is None:
        reply_message(
            reply_token=event.reply_token,
            text=(
                "ไม่พบเมนูที่เลือกค่ะ\n"
                "กรุณาพิมพ์ “Tata” เพื่อเปิดเมนูใหม่"
            ),
            show_menu=False,
        )
        return

    reply_message(
        reply_token=event.reply_token,
        text=answer_function(),
        # แสดงปุ่มเมนูซ้ำหลังตอบ
        show_menu=True,
    )