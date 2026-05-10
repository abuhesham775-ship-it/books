def format_book_info(book):
    if not book:
        return "📚 معلومات غير متوفرة"
    name = getattr(book, 'name', 'بدون عنوان')
    author = getattr(book, 'author', None)
    author_name = author.name if author and hasattr(author, 'name') else 'مؤلف غير معروف'
    return f"📖 {name}\n✍️ {author_name}"

def format_user_profile(user):
    if not user:
        return "👤 معلومات غير متوفرة"
    username = getattr(user, 'username', None)
    identifier = username or str(getattr(user, 'telegram_id', 'غير معروف'))
    return f"👤 المستخدم: {identifier}"

def truncate_text(text, max_length=50):
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."
