"""English translations."""

TEXTS: dict[str, str] = {
    # ── Main menu ──────────────────────────────────────────────────────────────
    "btn_catalog": "🛍 View product",
    "btn_my_purchases": "📦 My purchases",
    "btn_language": "🌐 Язык / Language",
    "btn_back": "◀️ Back",
    "btn_main_menu": "🏠 Main menu",
    "btn_cancel": "❌ Cancel",

    # ── Product card ───────────────────────────────────────────────────────────
    "btn_buy": "🛒 Buy for {price} ₽",
    "btn_buy_already": "📥 Download again",
    "btn_confirm_pay": "✅ Confirm payment",
    "btn_pay_robokassa": "💳 Go to payment",
    "btn_back_to_product": "◀️ Back to product",

    # ── Catalog texts ──────────────────────────────────────────────────────────
    "product_card": (
        "📦 <b>{name}</b>\n\n"
        "{description}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💵 Price: <b>{price_usd}</b> (~{price} ₽)\n"
        "{pdf_status}"
        "━━━━━━━━━━━━━━━━━━━━"
    ),
    "pdf_ready": "📄 File: ready to deliver\n",
    "pdf_missing": "⚠️ File: temporarily unavailable\n",
    "already_purchased": (
        "✅ <b>You have already purchased this product!</b>\n\n"
        "Click the button below to download the file again."
    ),

    # ── My purchases ───────────────────────────────────────────────────────────
    "purchases_empty": (
        "📦 <b>My purchases</b>\n\n"
        "You haven't made any purchases yet.\n\n"
        "Browse the catalog to buy a product!"
    ),
    "purchases_header": "📦 <b>My purchases</b>\n",
    "purchases_item": "{n}. {date} — <b>{amount} ₽</b>",

    # ── Purchase flow ──────────────────────────────────────────────────────────
    "confirm_title": "🛒 <b>Purchase confirmation</b>",
    "confirm_product": "📦 Product: <b>{name}</b>",
    "confirm_price_demo": "💰 Total: <b>{price_usd}</b> (~{price} ₽)",
    "confirm_price_base": "💵 Seller price: <b>{price_usd}</b> (~{price} ₽)",
    "confirm_commission": "🏦 Robokassa fee ({rate}%): ~{commission} ₽",
    "confirm_total": "💳 <b>Total to pay: {price_usd}</b> (~{price} ₽)",
    "confirm_demo_note": "<i>🧪 Demo mode — no real payment required</i>",
    "separator": "━━━━━━━━━━━━━━━━━━━━",

    # ── Success / delivery ─────────────────────────────────────────────────────
    "success": (
        "🎉 <b>Payment successful!</b>\n\n"
        "Thank you for your purchase! 📄 Your file is sent below. Save it!"
    ),
    "file_caption": "📄 {name}",
    "no_file": (
        "⚠️ *File temporarily unavailable*\n\n"
        "The administrator has been notified\\. We will send the file shortly\\."
    ),

    # ── Robokassa waiting ──────────────────────────────────────────────────────
    "robokassa_waiting": (
        "💳 *Payment via Robokassa*\n\n"
        "Product: *{name}*\n"
        "Amount: *{price_usd}* \\(~{price} ₽\\)\n"
        "Order number: `#{inv_id}`\n\n"
        "Click the button below to go to the payment page\\.\n\n"
        "_The file will be delivered automatically after payment\\._"
    ),
    "robokassa_test": "\n⚠️ _Test mode: no real money is charged_",

    # ── Language selection ─────────────────────────────────────────────────────
    "lang_select_title": "🌐 <b>Выбор языка / Language selection</b>",
    "lang_select_text": "Выберите язык интерфейса:\nChoose interface language:",
    "lang_set": "✅ Language changed to <b>English</b>",
    "btn_lang_ru": "🇷🇺 Русский",
    "btn_lang_en": "🇬🇧 English",

    # ── Welcome (fallback — overridden by product.welcome_text_en) ─────────────
    "welcome": (
        "🤖 <b>Welcome to AI Prompts Shop!</b>\n\n"
        "Here you can purchase an exclusive pack of premium AI prompts.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 <b>What's inside?</b>\n"
        "• 100+ tested prompts\n"
        "• Categories: business, marketing, coding, creativity\n"
        "• Ready to use right now\n"
        "• Compatible with ChatGPT, Claude, Gemini\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Choose an action below 👇"
    ),
}
