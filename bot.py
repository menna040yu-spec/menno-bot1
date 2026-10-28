import io
import zipfile
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageEnhance
from concurrent.futures import ThreadPoolExecutor, as_completed
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# 1. أمر /start: سحب الفصل كاملاً كملف ZIP
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = 'zip'
    context.user_data['state'] = 'waiting_for_chapter_number'
    await update.message.reply_text(
        "مرحباً بكِ في بوت سحب المانهوا 📥\n"
        "تم اختيار وضع **سحب الفصل كاملاً (ZIP)**.\n\n"
        "الرجاء إرسال **رقم الفصل** أولاً (مثلاً: 22):\n\n"
        "البوت من صنع مينو 🤍"
    )

# 2. أمر /merge: الدمج الذكي من الرابط
async def merge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = 'merge'
    context.user_data['state'] = 'waiting_for_chapter_number'
    await update.message.reply_text(
        "مرحباً بكِ في بوت الدمج الذكي 🔗\n"
        "تم اختيار وضع **دمج الفصل وضغط النتائج في ملف ZIP بأعلى جودة**.\n\n"
        "الرجاء إرسال **رقم الفصل** أولاً (مثلاً: 22):\n\n"
        "البوت من صنع مينو 🤍"
    )

# 3. أمر /enhance: رفع جودة صورة أو ملف مرسل يدوياً
async def enhance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = 'enhance'
    context.user_data['state'] = 'waiting_for_media_enhance'
    await update.message.reply_text(
        "✨ تم تفعيل وضع **رفع الجودة والتحسين**.\n\n"
        "الرجاء إرسال الصورة أو الملف (Document/Photo) الآن لتقوم مينو برفع نقائه بأعلى جودة وإرساله كملف! 🤍"
    )

# 4. أمر /merge_file: دمج صور أو ملفات مرسلة يدوياً
async def merge_file_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = 'merge_file'
    context.user_data['uploaded_files'] = []
    context.user_data['state'] = 'collecting_images_for_merge'
    await update.message.reply_text(
        "🔗 تم تفعيل وضع **الدمج اليدوي للملفات**.\n\n"
        "أرسلي الصور أو الملفات تباعاً (سواء كصور أو ملفات)، وعند الانتهاء تماماً اكتبي كلمة **`تم`** أو **`دمج`** لأسوي الدمج الذكي فوراً وأرسله كملف! 🤍"
    )

# 5. أمر /towebp: ضغط وتحويل الصور لـ WEBP
async def towebp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = 'towebp'
    context.user_data['state'] = 'waiting_for_media_towebp'
    await update.message.reply_text(
        "⚡ تم تفعيل وضع **ضغط وتحويل الصور إلى WEBP** (مثل towebp.io).\n\n"
        "أرسلي الصورة أو الملف الآن لأقوم بتحويله وضغطه وإرساله كملف جاهز! 🤍"
    )


def download_and_process(i, img_url, headers, chapter_num):
    for _ in range(3):
        try:
            img_response = requests.get(img_url, headers=headers, timeout=40)
            if img_response.status_code == 200:
                img = Image.open(io.BytesIO(img_response.content))
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='WEBP', quality=90, method=6)
                img_byte_arr.seek(0)
                filename = f"ch{chapter_num}_{i+1:03d}.webp"
                return i, filename, img_byte_arr.read()
        except:
            continue
    return i, None, None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip() if update.message.text else ""
    state = context.user_data.get('state')
    mode = context.user_data.get('mode')

    # معالجة الدمج اليدوي للملفات/الصور المرسلة
    if state == 'collecting_images_for_merge':
        if text.lower() in ['تم', 'done', 'دمج', 'merge']:
            images_list = context.user_data.get('uploaded_files', [])
            if not images_list:
                await update.message.reply_text("⚠️ لم تقومي بإرسال أي صور أو ملفات للدمج بعد!")
                return
            
            status_msg = await update.message.reply_text(f"🔗 جاري دمج الـ {len(images_list)} ملفاً المرسلة بذكاء...")
            
            pil_images = [Image.open(io.BytesIO(b)) for b in images_list]
            width = pil_images[0].width if pil_images else 800
            
            resized_batch = []
            for img in pil_images:
                if img.width != width:
                    img = img.resize((width, int(img.height * (width / img.width))))
                resized_batch.append(img)
                
            total_height = sum(img.height for img in resized_batch)
            merged_img = Image.new('RGB', (width, total_height))
            
            y_offset = 0
            for img in resized_batch:
                merged_img.paste(img, (0, y_offset))
                y_offset += img.height
                
            output_buffer = io.BytesIO()
            merged_img.save(output_buffer, format='JPEG', quality=95)
            output_buffer.seek(0)
            
            # إرسال النتيجة كملف دقيق وثابت
            await update.message.reply_document(
                document=output_buffer,
                filename="Manual_Merged_Result.jpg",
                caption="✨ تم دمج الصور والملفات المرسلة يدوياً بنجاح كملف بأعلى جودة!\n\nالبوت من صنع مينو 🤍"
            )
            context.user_data['state'] = None
            return

    # استقبال الصور أو الملفات للعمليات اليدوية (enhance, towebp, merge_file)
    if update.message.photo or update.message.document:
        try:
            if update.message.photo:
                photo_file = await update.message.photo[-1].get_file()
            else:
                photo_file = await update.message.document.get_file()
            
            file_bytes = await photo_file.download_as_bytearray()
        except Exception as e:
            await update.message.reply_text(f"⚠️ حدث خطأ أثناء استقبال الملف: {str(e)}")
            return
        
        if mode == 'enhance':
            await update.message.reply_text("✨ جاري رفع جودة وتحسين الملف المرسل...")
            img = Image.open(io.BytesIO(file_bytes))
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.5)
            
            out_buf = io.BytesIO()
            img.save(out_buf, format='JPEG', quality=95)
            out_buf.seek(0)
            
            # إرسال التحسين كملف
            await update.message.reply_document(
                document=out_buf,
                filename="Enhanced_Image.jpg",
                caption="✨ تم رفع جودة الصورة/الملف بنجاح وإرساله كملف نقي ومنقى تماماً!\n\nالبوت من صنع مينو 🤍"
            )
            context.user_data['state'] = None
            return

        elif mode == 'towebp':
            await update.message.reply_text("⚡ جاري الضغط والتحويل إلى WEBP...")
            img = Image.open(io.BytesIO(file_bytes))
            
            out_buf = io.BytesIO()
            img.save(out_buf, format='WEBP', quality=85, method=6)
            out_buf.seek(0)
            
            # إرسال التحويل كملف WEBP
            await update.message.reply_document(
                document=out_buf,
                filename="Converted_Image.webp",
                caption="⚡ تم التحويل إلى WEBP بجودة ممتازة وحجم خفيف (مثل towebp.io) كملف جاهز!\n\nالبوت من صنع مينو 🤍"
            )
            context.user_data['state'] = None
            return

        elif mode == 'merge_file':
            context.user_data['uploaded_files'].append(file_bytes)
            count = len(context.user_data['uploaded_files'])
            await update.message.reply_text(f"📥 تم استلام الملف رقم ({count}). أرسلي غيره، أو اكتبي **`تم`** للبدء بالدمج الفوري كملف!")
            return

    # سحب الفصول عبر الرابط (للأمرين start و merge)
    if state == 'waiting_for_chapter_number':
        context.user_data['chapter_num'] = text
        context.user_data['state'] = 'waiting_for_url'
        mode_name = "سحب ZIP" if mode == 'zip' else "الدمج الذكي من الموقع"
        await update.message.reply_text(f"تمام! رقم الفصل هو: ch{text} ({mode_name}) 📌\nدلوقتي ابعتي **رابط الفصل** عشان أبدأ الفحص والسحب بمهلة ممدودة:")
        return

    if state == 'waiting_for_url' or not state:
        url = text
        chapter_num = context.user_data.get('chapter_num', '1')
        
        status_msg = await update.message.reply_text("🔎 جاري الاتصال بالموقع وفحص الصفحة...")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url, headers=headers, timeout=180)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                images = soup.find_all('img')
                img_urls = [img.get('src') for img in images if img.get('src') and 'http' in img.get('src')]
                
                total_images = len(img_urls)
                if total_images == 0:
                    await status_msg.edit_text("عذراً، لم يتم العثور على صور في هذا الرابط.")
                    return

                await status_msg.edit_text(f"🎯 تم اكتشاف **{total_images} صورة** في الفصل!\n🚀 جاري السحب بالسرعة القصوى...")

                completed_count = 0
                results_dict = {}

                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(download_and_process, i, img_url, headers, chapter_num) for i, img_url in enumerate(img_urls)]
                    
                    for future in as_completed(futures):
                        i, filename, img_bytes = future.result()
                        if filename and img_bytes:
                            results_dict[i] = (filename, img_bytes)
                        
                        completed_count += 1
                        percent = int((completed_count / total_images) * 100)
                        filled_blocks = int(percent / 10)
                        bar = "█" * filled_blocks + "▒" * (10 - filled_blocks)
                        
                        try:
                            await status_msg.edit_text(
                                f"🎯 تم اكتشاف **{total_images} صورة** في الفصل!\n"
                                f"🚀 [{bar}] {percent}% - تم تحميل ({completed_count}/{total_images})..."
                            )
                        except:
                            pass

                downloaded_images_list = []
                for i in range(total_images):
                    if i in results_dict:
                        _, img_bytes = results_dict[i]
                        downloaded_images_list.append(img_bytes)

                # 1. وضع سحب الفصل (ZIP عادي)
                if mode == 'zip':
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for i in range(total_images):
                            if i in results_dict:
                                filename, img_bytes = results_dict[i]
                                zip_file.writestr(filename, img_bytes)
                    zip_buffer.seek(0)
                    
                    await status_msg.edit_text(
                        f"🎯 تم اكتشاف **{total_images} صورة** في الفصل!\n"
                        f"✅ [██████████] 100% - تم الانتهاء وجاري رفع الملف..."
                    )
                    
                    zip_filename = f"ch{chapter_num}.zip"
                    await update.message.reply_document(
                        document=zip_buffer,
                        filename=zip_filename,
                        caption=f"✨ تم سحب الفصل ch{chapter_num} بالسرعة الصاروخية وبصيغة WEBP كملف!\n\nالبوت من صنع مينو 🤍"
                    )

                # 2. وضع الدمج الذكي من الموقع وضغط النتائج في ملف ZIP
                elif mode == 'merge':
                    await status_msg.edit_text(f"🔗 جاري دمج الـ {total_images} صورة بأعلى جودة وتجميعها في ملف ZIP واحد...")
                    
                    target_count = total_images if total_images <= 16 else 14
                    batch_size = max(1, total_images // target_count)
                    
                    pil_images = [Image.open(io.BytesIO(b)) for b in downloaded_images_list]
                    width = pil_images[0].width if pil_images else 800
                    
                    merged_zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(merged_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as merged_zip:
                        for idx, start_idx in enumerate(range(0, len(pil_images), batch_size)):
                            batch = pil_images[start_idx:start_idx + batch_size]
                            if not batch:
                                continue
                            
                            resized_batch = []
                            for img in batch:
                                if img.width != width:
                                    img = img.resize((width, int(img.height * (width / img.width))))
                                resized_batch.append(img)
                                
                            total_height = sum(img.height for img in resized_batch)
                            merged_img = Image.new('RGB', (width, total_height))
                            
                            y_offset = 0
                            for img in resized_batch:
                                merged_img.paste(img, (0, y_offset))
                                y_offset += img.height
                                
                            output_buffer = io.BytesIO()
                            merged_img.save(output_buffer, format='JPEG', quality=95)
                            output_buffer.seek(0)
                            
                            merged_zip.writestr(f"ch{chapter_num}_merged_{idx+1:02d}.jpg", output_buffer.read())

                    merged_zip_buffer.seek(0)

                    await status_msg.edit_text(f"📤 جاري إرسال ملف الـ ZIP المدمج بأعلى جودة كملف...")
                    
                    await update.message.reply_document(
                        document=merged_zip_buffer,
                        filename=f"ch{chapter_num}_Smart_Merged.zip",
                        caption=f"🔗 إليكِ ملف الدمج الذكي للفصل ch{chapter_num} (مضغوط ZIP بأعلى جودة كملف)\n\nالبوت من صنع مينو 🤍"
                    )

                context.user_data['state'] = None
                
            else:
                await status_msg.edit_text(f"حدث خطأ في الاتصال بالموقع (كود: {response.status_code})")
                
        except Exception as e:
            await status_msg.edit_text(f"حدث خطأ (انتهت مهلة الـ 3 دقائق، جربي مرة أخرى): {str(e)}")

if __name__ == '__main__':
    TOKEN = "9028638207:AAFxD4MnnCaNnHyAtvxS6przhHrQHaXLybE"
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("merge", merge_command))
    app.add_handler(CommandHandler("enhance", enhance_command))
    app.add_handler(CommandHandler("merge_file", merge_file_command))
    app.add_handler(CommandHandler("towebp", towebp_command))
    
    # تصحيح شامل لفلتر الرسائل لدعم الصور والملفات بمختلف أنواعها
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.Document.ALL) & (~filters.COMMAND), handle_message))
    
    print("البوت الخارق يعمل الآن بكافة الأدوات وتحسينات الملفات... 🤍")
    app.run_polling()