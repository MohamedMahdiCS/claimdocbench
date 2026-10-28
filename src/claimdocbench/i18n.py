"""Labels and translations for documents in English (en), Bahasa Melayu (ms) and Chinese (zh).

Canonical gold values stay language-independent (ISO dates, decimals, English catalog names);
only what is *printed* changes with the language.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from datetime import date
from typing import Final

LANGUAGES: Final = ("en", "ms", "zh")

LABELS: dict[str, dict[str, str]] = {
    "en": {
        "official_receipt": "OFFICIAL RECEIPT",
        "tax_invoice": "TAX INVOICE",
        "receipt": "RECEIPT",
        "receipt_no": "Receipt",
        "invoice_no": "Invoice no",
        "date": "Date",
        "patient": "Patient",
        "doctor": "Doctor",
        "attending": "Attending",
        "total": "TOTAL",
        "total_paid": "Total paid",
        "paid_by": "Paid by",
        "tel": "Tel",
        "reg_no": "Reg No",
        "description": "Description",
        "amount": "Amount",
        "thanks": "Thank you. Get well soon!",
        "computer": "This is a computer-generated receipt.",
        "received_from": "Received from",
        "signature": "Authorised signature",
        "mc_title": "MEDICAL CERTIFICATE",
        "mc_certify": "This is to certify that",
        "mc_unfit": "was examined by me and is unfit for work for",
        "mc_days": "day(s) from",
        "mc_to": "to",
        "diagnosis": "Diagnosis",
        "medical_officer": "Medical Officer",
        "ref_to": "To: The Consultant,",
        "ref_re": "RE: REFERRAL",
        "ref_body": "Dear Doctor, I would be grateful if you could kindly review the above patient for",
        "ref_thanks": "Thank you for your assistance.",
        "ref_sign": "Yours sincerely,",
        "cf_title": "GROUP OUTPATIENT CLAIM FORM",
        "cf_a": "Section A — Member",
        "cf_b": "Section B — Treatment",
        "cf_c": "Section C — Payment",
        "cf_remarks": "Remarks",
        "employer": "Employer",
        "member_id": "Member ID",
        "member_name": "Member name",
        "patient_name": "Patient name",
        "relationship": "Relationship to member",
        "clinic": "Clinic / hospital",
        "visit_date": "Date of treatment",
        "visit_type": "Type of visit",
        "referred": "Referred by a GP?",
        "amount_claimed": "Total amount claimed",
        "bank": "Bank",
        "account": "Account no.",
        "declaration": "I declare that the information given is true and complete, and that the "
        "attached receipts are original and have not been claimed elsewhere.",
        "signature_short": "Signature",
    },
    "ms": {
        "official_receipt": "RESIT RASMI",
        "tax_invoice": "INVOIS CUKAI",
        "receipt": "RESIT",
        "receipt_no": "No. Resit",
        "invoice_no": "No. Invois",
        "date": "Tarikh",
        "patient": "Pesakit",
        "doctor": "Doktor",
        "attending": "Doktor bertugas",
        "total": "JUMLAH",
        "total_paid": "Jumlah dibayar",
        "paid_by": "Bayaran",
        "tel": "Tel",
        "reg_no": "No. Daftar",
        "description": "Keterangan",
        "amount": "Amaun",
        "thanks": "Terima kasih. Semoga cepat sembuh!",
        "computer": "Resit ini dijana oleh komputer.",
        "received_from": "Diterima daripada",
        "signature": "Tandatangan yang diberi kuasa",
        "mc_title": "SIJIL CUTI SAKIT",
        "mc_certify": "Dengan ini disahkan bahawa",
        "mc_unfit": "telah diperiksa oleh saya dan tidak sihat untuk bekerja selama",
        "mc_days": "hari dari",
        "mc_to": "hingga",
        "diagnosis": "Diagnosis",
        "medical_officer": "Pegawai Perubatan",
        "ref_to": "Kepada: Pakar Perunding,",
        "ref_re": "PER: RUJUKAN",
        "ref_body": "Tuan/Puan, saya amat menghargai jika tuan/puan dapat memeriksa pesakit di "
        "atas untuk",
        "ref_thanks": "Terima kasih atas bantuan tuan/puan.",
        "ref_sign": "Yang benar,",
        "cf_title": "BORANG TUNTUTAN PESAKIT LUAR BERKUMPULAN",
        "cf_a": "Bahagian A — Ahli",
        "cf_b": "Bahagian B — Rawatan",
        "cf_c": "Bahagian C — Bayaran",
        "cf_remarks": "Catatan",
        "employer": "Majikan",
        "member_id": "No. Ahli",
        "member_name": "Nama ahli",
        "patient_name": "Nama pesakit",
        "relationship": "Hubungan dengan ahli",
        "clinic": "Klinik / hospital",
        "visit_date": "Tarikh rawatan",
        "visit_type": "Jenis lawatan",
        "referred": "Dirujuk oleh doktor am?",
        "amount_claimed": "Jumlah tuntutan",
        "bank": "Bank",
        "account": "No. akaun",
        "declaration": "Saya mengaku bahawa maklumat yang diberi adalah benar dan lengkap, dan "
        "resit yang dilampirkan adalah asal serta belum dituntut di tempat lain.",
        "signature_short": "Tandatangan",
    },
    "zh": {
        "official_receipt": "正式收据",
        "tax_invoice": "税务发票",
        "receipt": "收据",
        "receipt_no": "收据号码",
        "invoice_no": "发票号码",
        "date": "日期",
        "patient": "病人",
        "doctor": "医生",
        "attending": "主治医生",
        "total": "总额",
        "total_paid": "已付总额",
        "paid_by": "付款方式",
        "tel": "电话",
        "reg_no": "注册号码",
        "description": "项目",
        "amount": "金额",
        "thanks": "谢谢光临，祝早日康复！",
        "computer": "此收据由电脑生成。",
        "received_from": "收款自",
        "signature": "授权签名",
        "mc_title": "医疗证明书（病假单）",
        "mc_certify": "兹证明",
        "mc_unfit": "经本人诊断，不宜工作",
        "mc_days": "天，自",
        "mc_to": "至",
        "diagnosis": "诊断",
        "medical_officer": "医生",
        "ref_to": "致：专科顾问医生",
        "ref_re": "事由：转诊",
        "ref_body": "医生您好，烦请为上述病人检查，病因：",
        "ref_thanks": "感谢您的协助。",
        "ref_sign": "此致",
        "cf_title": "团体门诊索赔表格",
        "cf_a": "甲部 — 会员资料",
        "cf_b": "乙部 — 治疗资料",
        "cf_c": "丙部 — 付款资料",
        "cf_remarks": "备注",
        "employer": "雇主",
        "member_id": "会员编号",
        "member_name": "会员姓名",
        "patient_name": "病人姓名",
        "relationship": "与会员关系",
        "clinic": "诊所 / 医院",
        "visit_date": "就诊日期",
        "visit_type": "就诊类型",
        "referred": "是否由家庭医生转诊？",
        "amount_claimed": "索赔总额",
        "bank": "银行",
        "account": "账户号码",
        "declaration": "本人声明以上资料真实完整，所附收据均为正本，且未在其他地方索赔。",
        "signature_short": "签名",
    },
}

VALUES: dict[str, dict[str, str]] = {
    "en": {
        "GP": "General practitioner",
        "SPECIALIST": "Specialist",
        "Yes": "Yes",
        "No": "No",
        "N/A": "N/A",
        "self": "Self",
        "spouse": "Spouse",
        "child": "Child",
        "Cash": "Cash",
        "Debit card": "Debit card",
        "Credit card": "Credit card",
        "QR payment": "QR payment",
    },
    "ms": {
        "GP": "Doktor am",
        "SPECIALIST": "Pakar",
        "Yes": "Ya",
        "No": "Tidak",
        "N/A": "Tidak berkenaan",
        "self": "Diri sendiri",
        "spouse": "Pasangan",
        "child": "Anak",
        "Cash": "Tunai",
        "Debit card": "Kad debit",
        "Credit card": "Kad kredit",
        "QR payment": "Bayaran QR",
    },
    "zh": {
        "GP": "家庭医生",
        "SPECIALIST": "专科",
        "Yes": "是",
        "No": "否",
        "N/A": "不适用",
        "self": "本人",
        "spouse": "配偶",
        "child": "子女",
        "Cash": "现金",
        "Debit card": "借记卡",
        "Credit card": "信用卡",
        "QR payment": "二维码付款",
    },
}

ITEMS: dict[str, dict[str, str]] = {
    "Consultation fee": {"ms": "Caj konsultasi", "zh": "诊疗费"},
    "Doctor consultation": {"ms": "Konsultasi doktor", "zh": "医生诊疗"},
    "Specialist consultation": {"ms": "Konsultasi pakar", "zh": "专科诊疗费"},
    "Paracetamol 500mg x 10": {"ms": "Paracetamol 500mg x 10", "zh": "扑热息痛 500mg x 10"},
    "Amoxicillin 500mg x 15": {"ms": "Amoxicillin 500mg x 15", "zh": "阿莫西林 500mg x 15"},
    "Loratadine 10mg x 10": {"ms": "Loratadine 10mg x 10", "zh": "氯雷他定 10mg x 10"},
    "Cough syrup 100ml": {"ms": "Ubat batuk 100ml", "zh": "止咳糖浆 100ml"},
    "Omeprazole 20mg x 14": {"ms": "Omeprazole 20mg x 14", "zh": "奥美拉唑 20mg x 14"},
    "Ibuprofen 400mg x 10": {"ms": "Ibuprofen 400mg x 10", "zh": "布洛芬 400mg x 10"},
    "Salbutamol inhaler": {"ms": "Inhaler salbutamol", "zh": "沙丁胺醇吸入器"},
    "Metformin 500mg x 30": {"ms": "Metformin 500mg x 30", "zh": "二甲双胍 500mg x 30"},
    "Wound dressing": {"ms": "Cucian luka", "zh": "伤口换药"},
    "Nebuliser treatment": {"ms": "Rawatan nebulizer", "zh": "雾化治疗"},
    "Ear irrigation": {"ms": "Cucian telinga", "zh": "耳道冲洗"},
    "Minor suturing": {"ms": "Jahitan kecil", "zh": "小型缝合"},
    "Full blood count": {"ms": "Ujian darah penuh (FBC)", "zh": "全血细胞计数"},
    "Urine FEME": {"ms": "Ujian air kencing FEME", "zh": "尿液常规检查"},
    "HbA1c test": {"ms": "Ujian HbA1c", "zh": "糖化血红蛋白检测"},
    "Lipid profile": {"ms": "Profil lipid", "zh": "血脂检查"},
    "Vitamin C 1000mg x 30": {"ms": "Vitamin C 1000mg x 30", "zh": "维生素C 1000mg x 30"},
    "Multivitamin tablets x 30": {"ms": "Tablet multivitamin x 30", "zh": "复合维生素片 x 30"},
    "Fish oil capsules x 60": {"ms": "Kapsul minyak ikan x 60", "zh": "鱼油胶囊 x 60"},
    "Herbal tonic 500ml": {"ms": "Tonik herba 500ml", "zh": "草本补品 500ml"},
    "Acne laser session": {"ms": "Sesi laser jerawat", "zh": "祛痘激光疗程"},
    "Skin whitening cream": {"ms": "Krim pemutih kulit", "zh": "美白霜"},
    "Chemical peel": {"ms": "Rawatan kupasan kimia", "zh": "化学换肤"},
    "Fertility consultation": {"ms": "Konsultasi kesuburan", "zh": "生育咨询"},
    "Ovulation induction": {"ms": "Rawatan induksi ovulasi", "zh": "促排卵治疗"},
    "Scaling and polishing": {"ms": "Cuci dan gilap gigi", "zh": "洗牙抛光"},
    "Tooth filling": {"ms": "Tampalan gigi", "zh": "补牙"},
    "Dental X-ray": {"ms": "X-ray gigi", "zh": "牙科X光"},
    "Health screening package": {"ms": "Pakej saringan kesihatan", "zh": "健康检查配套"},
    "Annual medical check-up": {"ms": "Pemeriksaan kesihatan tahunan", "zh": "年度体检"},
}

DIAGNOSIS_TEXT: dict[str, dict[str, str]] = {
    "J06.9": {"ms": "Jangkitan saluran pernafasan atas akut", "zh": "急性上呼吸道感染"},
    "A09": {"ms": "Gastroenteritis akut", "zh": "急性肠胃炎"},
    "J02.9": {"ms": "Faringitis akut", "zh": "急性咽炎"},
    "M54.5": {"ms": "Sakit belakang bawah", "zh": "下背痛"},
    "L30.9": {"ms": "Dermatitis", "zh": "皮炎"},
    "H10.9": {"ms": "Konjunktivitis", "zh": "结膜炎"},
    "R50.9": {"ms": "Demam", "zh": "发烧"},
    "E11.9": {"ms": "Diabetes mellitus jenis 2", "zh": "2型糖尿病"},
    "I10": {"ms": "Hipertensi", "zh": "高血压"},
    "J45.9": {"ms": "Asma", "zh": "哮喘"},
    "E78.5": {"ms": "Hiperlipidemia", "zh": "高血脂"},
}

MS_MONTHS = ["Jan", "Feb", "Mac", "Apr", "Mei", "Jun", "Jul", "Ogo", "Sep", "Okt", "Nov", "Dis"]
EN_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def item_text(description: str, lang: str) -> str:
    return description if lang == "en" else ITEMS.get(description, {}).get(lang, description)


def diagnosis_text(code: str, english: str, lang: str) -> str:
    return english if lang == "en" else DIAGNOSIS_TEXT.get(code, {}).get(lang, english)


def value(key: str, lang: str) -> str:
    return VALUES[lang].get(key, key)


def date_formatter(rng: random.Random, lang: str) -> tuple[str, Callable[[date], str]]:
    """Pick a date style for a document. Returns (style name, formatting function)."""
    styles = ["dmy_slash", "dmy_dash", "iso", "d_mon_y"]
    if lang == "zh":
        styles.append("zh")
    style = rng.choice(styles)

    def fmt(x: date) -> str:
        if style == "dmy_slash":
            return f"{x.day:02d}/{x.month:02d}/{x.year}"
        if style == "dmy_dash":
            return f"{x.day:02d}-{x.month:02d}-{x.year}"
        if style == "iso":
            return x.isoformat()
        if style == "zh":
            return f"{x.year}年{x.month}月{x.day}日"
        months = MS_MONTHS if lang == "ms" else EN_MONTHS
        return f"{x.day} {months[x.month - 1]} {x.year}"

    return style, fmt
