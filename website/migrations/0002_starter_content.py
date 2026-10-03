from django.db import migrations

SERVICES = [
    ("🌐", "Internet Access", "Browsing, email, social media, online applications and research."),
    ("💻", "Computer Rental", "Pay for the time you use a computer."),
    ("🖨️", "Printing", "Black-and-white and colour printing."),
    ("📄", "Photocopying", "Copies of documents and IDs."),
    ("📑", "Scanning", "Scan documents and send them digitally."),
    ("⌨️", "Typing & Document Preparation", "Letters, assignments, reports, CVs and applications."),
    ("📋", "CV & Job Application Services", "We create and edit your CV and help with online job applications."),
    ("📠", "Document Services", "Formatting, editing, converting and preparing documents."),
    ("🏛️", "Online Government Services", "Help with online government applications and forms."),
    ("🎓", "Online Applications", "University, college, scholarship and examination applications."),
    ("💳", "Online Payments & Services", "Help with legitimate online transactions and registrations."),
    ("📧", "Email Services", "Create an account, send emails and attach documents."),
    ("💾", "File Services", "Download, upload, transfer and store your documents."),
    ("🖼️", "Graphic & Design Services", "Basic flyers, posters, invitations and other documents."),
    ("📱", "Digital Assistance", "Help with basic computer, internet and software tasks."),
]


def add_content(apps, schema_editor):
    Service = apps.get_model("website", "Service")
    SiteInfo = apps.get_model("website", "SiteInfo")
    if not Service.objects.exists():
        for i, (icon, title, desc) in enumerate(SERVICES, start=1):
            Service.objects.create(icon=icon, title=title, description=desc, order=i)
    if not SiteInfo.objects.exists():
        # PLACEHOLDERS: replace these in the admin site (/admin/ > Website details)
        SiteInfo.objects.create(
            phone="+263 77 000 0000",
            whatsapp="263770000000",
            email="hello@example.com",
            address="Your street address, Your town",
            opening_hours="Mon-Fri: 08:00 - 18:00\nSat: 08:00 - 16:00\nSun: Closed",
        )


class Migration(migrations.Migration):
    dependencies = [("website", "0001_initial")]
    operations = [migrations.RunPython(add_content, migrations.RunPython.noop)]
