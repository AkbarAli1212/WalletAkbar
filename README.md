# 💼 BudgetBakers Wallet Telegram Bot (بـوت تـسـجـيـل الـمـصـاريـف)

بوت تليجرام متطور، فائق السرعة وخفيف الوزن مبني بلغة **Python 3.11+** بشكل غير متزامن بالكامل (Asynchronous)، مصمم للربط المباشر مع تطبيق **BudgetBakers Wallet** عبر الـ REST API الرسمي لتسجيل المصاريف والإيرادات فوراً بمجرد كتابة نص سريع أو إعادة توجيه رسائل البنوك السعودية.

---

## 🌟 المزايا الرئيسية (Key Features)

1. **أمان تام وقائمة بيضاء صارمة (Strict Whitelisting):**
   - حماية مطلقة؛ البوت مبرمج لمعالجة رسائل معرف تليجرام المحدد في `ALLOWED_TELEGRAM_USER_ID` فقط.
   - يتم إسقاط أو رفض أي رسائل من مستخدمين غير مصرح لهم فوراً دون تسريب أي بيانات.

2. **نمطان ذكيان لاستخراج البيانات (Dual Parsing Engine):**
   - **النمط الأول: التسجيل السريع (Quick Text Entry):**
     - أمثلة: `بنزين 50`، `Plan b 15.5`، `مازة 22`، `50 بنزين`، `دخل 300 دورة`، `راتب 8000`، `300 استلمت كاش`.
     - يدعم الأرقام العربية والإنجليزية (`٥٠` و `50`).
     - تحديد نوع العملية تلقائياً (مصروف افتراضياً، أو دخل عند وجود كلمات مثل `دخل`، `سيل`، `راتب`، `إيداع`، `استلمت`).
   - **النمط الثاني: محرك قراءة رسائل البنوك السعودية (Saudi Bank SMS Engine):**
     - يدعم كافة صيغ الرسائل النصية من: **مصرف الراجحي، البنك الأهلي السعودي (SNB)، بنك الرياض، مصرف الإنماء، البنك السعودي الأول (SAB)، بنك البلاد، stc pay، urpay**، وغيرها.
     - استخراج المبلغ بدقة، اسم المتجر/المحل، تاريخ ووقت العملية، وآخر 4 أرقام من البطاقة/الحساب.

3. **تصنيف ذكي وتلقائي (Smart Category Mapping):**
   - مطابقة الكلمات المفتاحية لأشهر المتاجر في السعودية مع تصنيفات Wallet الرسمية:
     - ⛽ **الوقود (Fuel):** محطة، بنزين، ادريس، الدريس، ساسكو، sasco، aldrees، بترومين.
     - ☕ **كافيه ومقهى (Bar, cafe):** كوفي، كافيه، Plan B، قهوة، ستاربكس، دانكن، بارنز، Half Million، د.كيف.
     - 🍔 **مطاعم ووجبات (Restaurant, fast-food):** مازة، مطعم، برقرايزر، البيك، شاورمر، ماك، كودو، هرفي، شاورما، وجبة.
     - 🛒 **بقالة وسوبرماركت (Groceries):** بنده، panda، بقالة، تموينات، أسواق، العثيم، الدانوب، التميمي، كارفور، لولو.
     - 💻 **برامج واشتراكات (Software, apps, games):** Google, Apple, Render, Vercel, OpenAI, ChatGPT, Cursor, Netflix, Spotify.
     - 🟢 **دخل (Income):** عند وجود عمليات إيداع أو حوالات واردة.
     - 📦 **تصنيف عام (General/Other):** كخيار احتياطي عند عدم مطابقة أي كلمة.

4. **بطاقة تأكيد تفاعلية وتجربة مستخدم متميزة (Interactive Telegram UX):**
   - فور تسجيل العملية، يرسل البوت بطاقة تأكيد فخمة ومنظمة:
     ```text
     ✅ تم تسجيل العملية بنجاح في Wallet
     ━━━━━━━━━━━━━━━━━━━━
     💵 المبلغ: 52.67 SAR (🔴 مصروف)
     🏷️ التصنيف: الوقود (Fuel)
     🏪 المحل / الوصف: محطة الدريس
     💳 الحساب: Main (بطاقة **1234)
     📅 التاريخ: 2026-09-25 14:30
     📝 ملاحظة: Al Rajhi Bank - شراء بنكي
     ━━━━━━━━━━━━━━━━━━━━
     ```
   - أزرار تفاعلية فورية مدمجة:
     - `[ 🏷️ تعديل التصنيف ]` لإعادة تصنيف العملية بضغطة زر وتحديثها في Wallet مباشرة عبر API.
     - `[ 🗑️ حذف العملية ]` لحذف العملية نهائياً من محفظة Wallet في حال تم تسجيلها بالخطأ.

5. **المستشار المالي الذكي والمحادثة الطبيعية (Smart Financial Advisor):**
   - اسأل البوت باللغة العامية أو الفصحى مثل:
     - <i>«كم في حسابي؟»</i>، <i>«كم رصيدي؟»</i>، <i>«كم باقي معي؟»</i>
   - يجيبك بذكاء وبطريقة تحليلية متكاملة:
     - رصيد الحساب المتاح بدقة.
     - تقييم ذكي لمستوى السيولة والأمان المالي.
     - نسبة التوفير التراكمية من إجمالي الدخل.
     - ملخص مصروفات اليوم وعدد العمليات.
     - آخر عملية مسجلة بتفاصيلها.
     - نصيحة مالية ذكية ومخصصة لحالتك.
   - يدعم أسئلة المصاريف: <i>«كم صرفت اليوم؟»</i> و <i>«آخر العمليات»</i>.
   - أزرار تفاعلية تحت الرد: `[ 🔄 تحديث الرصيد ]`، `[ 🛒 صرفيات اليوم ]`، `[ 📊 أكبر التصنيفات ]`، `[ 🕒 آخر العمليات ]`، `[ 💡 نصيحة مالية ذكية ]`.

6. **أوامر استعلامية سريعة:**
   - `/start` - الترحيب وتوضيح طرق الاستخدام وأمثلة.
   - `/balance` - تحليل ذكي وشامل للرصيد والوضع المالي.
   - `/categories` - استعراض التصنيفات المربوطة وكلماتها المفتاحية.
   - `/help` - دليل الاستخدام السريع.

---

## 📁 هيكلية المشروع (Project Structure)

```text
WalletAkbar/
├── bot.py                  # ملف البوت الأساسي (aiogram v3) ومعالجة الأحداث والواجهة
├── smart_assistant.py      # محرك المستشار المالي الذكي وتحليل الأسئلة والرصيد
├── wallet_client.py        # عميل HTTP غير متزامن للتواصل مع BudgetBakers REST API
├── parser.py               # محرك تحليل الرسائل (Regex للرسائل البنكية + التسجيل السريع)
├── config.py               # إدارة الإعدادات والتحقق من صحتها عبر Pydantic Settings
├── get_metadata.py         # أداة جلب معرفات الحسابات والتصنيفات من حساب المستخدم
├── verify_all.py           # فحص صحة وتكامل واتصال النظام كاملاً
├── test_suite.py           # اختبارات شاملة لكافة حالات التحليل والتصنيف والذكاء
├── requirements.txt        # مكتبات بايثون المطلوبة
├── Dockerfile              # بناء صورة دوكر خفيفة وآمنة
├── docker-compose.yml      # تشغيل فوري عبر دوكر كومبوز
├── .env.example            # قالب متغيرات البيئة
├── .env                    # ملف الإعدادات النشط (يحتوي على المفاتيح)
└── README.md               # التوثيق الشامل
```

---

## ⚙️ الإعداد والتشغيل المحلي (Local Setup)

### 1. المتطلبات:
- بايثون 3.11 أو أحدث مثبت على جهازك.

### 2. تجهيز البيئة الافتراضية وتثبيت المكتبات:
```bash
# إنشاء بيئة افتراضية
python -m venv .venv

# تفعيل البيئة:
# على Windows (PowerShell):
.venv\Scripts\Activate.ps1
# على Linux/macOS:
source .venv/bin/activate

# تثبيت المكتبات:
pip install -r requirements.txt
```

### 3. إعداد ملف `.env`:
انسخ `.env.example` إلى `.env` وضع بياناتك:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxyz
TELEGRAM_USER_ID=123456789
WALLET_API_TOKEN=your_wallet_jwt_api_token_here
WALLET_DEFAULT_ACCOUNT_ID=your_default_account_uuid_here
```

### 4. جلب المعرفات عبر أداة `get_metadata.py`:
يمكنك في أي وقت فحص حساباتك وتصنيفاتك من خلال تشغيل:
```bash
python get_metadata.py
```

### 5. تشغيل البوت:
```bash
python bot.py
```

---

## 🚀 النشر والتشغيل المستمر 24/7 (24/7 Deployment Guide)

### الخيار 1: باستخدام Docker & Docker Compose (موصى به لأي VPS)
1. تأكد من وجود ملف `.env` في المجلد.
2. شغّل الحاوية في الخلفية:
```bash
docker compose up -d --build
```
3. لمتابعة السجلات (Logs):
```bash
docker compose logs -f
```

---

### الخيار 2: النشر السحابي كـ Background Worker (Render / Koyeb / Railway)
البوت يعمل بنظام **Long Polling** غير المتزامن، لذا فهو يعمل كـ **Background Worker** ممتاز لا يتطلب فتح أي منافذ HTTP واردة:

#### للنشر على Render:
1. ارفع المشروع إلى مستودع خاص على GitHub.
2. في لوحة تحكم Render، اختر **New +** ثم **Background Worker**.
3. حدد المستودع الخاص بك.
4. اضبط الإعدادات:
   - **Environment:** `Python 3` أو `Docker`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
5. في قسم **Environment Variables**، أضف المتغيرات الموجودة في `.env`.
6. انقر على **Create Background Worker**.

#### للنشر على Koyeb:
1. أنشئ خدمة جديدة واختر **Worker Service**.
2. اربط مستودع GitHub الخاص بك.
3. اضبط أمر التشغيل على `python bot.py`.
4. أضف متغيرات البيئة من ملف `.env`.
5. سيبدأ البوت بالعمل تلقائياً على مدار الساعة!

---

### الخيار 3: التشغيل عبر Systemd Service (على سيرفر Linux / Ubuntu)
1. أنشئ ملف خدمة:
```bash
sudo nano /etc/systemd/system/wallet-bot.service
```
2. ضع المحتوى التالي (مع تعديل المسار واسم المستخدم):
```ini
[Unit]
Description=BudgetBakers Wallet Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/WalletAkbar
ExecStart=/home/ubuntu/WalletAkbar/.venv/bin/python bot.py
Restart=always
RestartSec=10
EnvironmentFile=/home/ubuntu/WalletAkbar/.env

[Install]
WantedBy=multi-user.target
```
3. تفعيل وتشغيل الخدمة:
```bash
sudo systemctl daemon-reload
sudo systemctl enable wallet-bot
sudo systemctl start wallet-bot
```
4. فحص حالة البوت:
```bash
sudo systemctl status wallet-bot
```

---

## 🛡️ الأمان والخصوصية (Security)
- البوت لا يخزن أي سجلات بطاقات ائتمانية أو بيانات بنكية حساسة في قواعد بيانات خارجية.
- الاتصال مع خوادم BudgetBakers يتم عبر بروتوكول TLS 1.3 مشفر مباشرة.
- الـ Middleware يمنع أي شخص غريب من التفاعل مع البوت أو استعراض رصيدك أو تسجيل عمليات في حسابك.
