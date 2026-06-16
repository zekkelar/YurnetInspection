#!/usr/bin/env python3
# SHADOW BOT V4 - Async Telegram Bot v20.x
# Unit-based process manager dengan psutil (akurat di Termux)

import os
import sys
import subprocess
import json
import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

# ===== KONFIGURASI =====
BOT_TOKEN = "8319020434:AAHM1hNMZJo3DjeHBUNfg5WkL7OWVgd15dk"
ALLOWED_USERS = []  # Kosongin = semua boleh
AUDIT_LOG_FILE = "audit.log"
PROCESS_DB = "unit_processes.json"
LOG_DIR = "logs"

os.makedirs(LOG_DIR, exist_ok=True)

# ===== SETUP LOGGING =====
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== COBA IMPORT PSUTIL (AKURAT) =====
try:
    import psutil
    HAS_PSUTIL = True
    logger.info("✓ psutil loaded - process detection akurat")
except ImportError:
    HAS_PSUTIL = False
    logger.warning("⚠️ psutil tidak ada, fallback ke os.kill")

# ===== DATABASE FUNCTIONS =====
def load_db():
    if os.path.exists(PROCESS_DB):
        try:
            with open(PROCESS_DB, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_db(db):
    with open(PROCESS_DB, 'w') as f:
        json.dump(db, f, indent=2)

def is_process_alive(pid):
    """Cek apakah proses masih hidup (Termux compatible)"""
    if HAS_PSUTIL:
        try:
            psutil.Process(pid)
            return True
        except psutil.NoSuchProcess:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

def clean_dead_processes(db):
    """Hapus proses mati dari database"""
    cleaned = {}
    for unit, info in db.items():
        pid = info.get('pid')
        if pid and is_process_alive(pid):
            cleaned[unit] = info
        else:
            logger.info(f"Unit {unit} process {pid} is dead, removing")
    return cleaned

def is_unit_running(unit):
    db = load_db()
    db = clean_dead_processes(db)
    save_db(db)
    return str(unit) in db

def get_unit_info(unit):
    db = load_db()
    db = clean_dead_processes(db)
    save_db(db)
    return db.get(str(unit))

def lock_unit(unit, pid, command, user, chat_id, log_file):
    db = load_db()
    db = clean_dead_processes(db)
    db[str(unit)] = {
        'pid': pid,
        'command': command,
        'user': user,
        'chat_id': chat_id,
        'started': datetime.now().isoformat(),
        'log_file': log_file,
        'unit': unit
    }
    save_db(db)

def unlock_unit(unit):
    db = load_db()
    if str(unit) in db:
        del db[str(unit)]
        save_db(db)
        return True
    return False

def clear_all_units():
    """Paksa hapus semua unit"""
    if os.path.exists(PROCESS_DB):
        os.remove(PROCESS_DB)
        return True
    return False

# ===== AUTH DECORATOR =====
def restricted(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if ALLOWED_USERS and user_id not in ALLOWED_USERS:
            await update.message.reply_text("❌ Akses ditolak!")
            return
        return await func(update, context)
    return wrapper

# ===== COMMAND HANDLERS =====

def auth_audit(func):
    """Gabungan restricted + audit"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_name = update.effective_user.full_name or update.effective_user.username or str(user_id)
        
        # Dapatkan command dan args
        command = func.__name__.replace('_command', '')
        args = ' '.join(context.args) if context.args else ''
        
        # Cek auth
        if ALLOWED_USERS and user_id not in ALLOWED_USERS:
            await update.message.reply_text("❌ Akses ditolak!")
            audit_log(user_id, user_name, command, args, "ACCESS DENIED")
            return
        
        # Jalankan fungsi
        try:
            result = await func(update, context)
            audit_log(user_id, user_name, command, args, "SUCCESS")
            return result
        except Exception as e:
            audit_log(user_id, user_name, command, args, f"ERROR: {str(e)[:50]}")
            raise
    
    return wrapper


@auth_audit
async def unit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan daftar titik inspeksi untuk unit tertentu dari unitElectrical.json"""
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "❌ *Format:* `/unit 1` atau `/unit 2`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    unit = args[0]
    json_file = 'unitElectrical.json'
    
    if not os.path.exists(json_file):
        await update.message.reply_text(
            "❌ *File unitElectrical.json tidak ditemukan!*",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if unit not in data:
            available = ', '.join(sorted(data.keys(), key=int))
            await update.message.reply_text(
                f"❌ *Unit {unit} tidak ditemukan!*\n"
                f"Unit tersedia: {available}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        points = data[unit]
        sorted_points = sorted(points.items(), key=lambda x: int(x[0]))
        
        response = f"*🔧 UNIT {unit} - DAFTAR TITIK INSPEKSI*\n\n"
        response += "```\n"
        response += f"{'No':<4} {'Point Name'}\n"
        response += "-" * 50 + "\n"
        
        for idx, (point_id, point_data) in enumerate(sorted_points, 1):
            name = point_data.get('PointName', '-')[:40]
            route = point_data.get('RouteName', '-')[:20]
            response += f"{point_id:<4} {name}\n"
        
        response += "```\n"
        response += f"\n📊 *Total:* {len(points)} titik\n"
        response += f"📍 *Route:* {sorted_points[0][1].get('RouteName', '-') if sorted_points else '-'}\n\n"
        response += "Gunakan `/inspeksi unit X user Y`\n"
        response += "Skip titik: `/inspeksi unit X user Y exceptual 1,2,3`"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error membaca file: `{str(e)}`",
            parse_mode=ParseMode.MARKDOWN
        )

@auth_audit
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 *STANLEY - SHADOW CORE BOT* 🔥\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📋 *COMMANDS TERSEDIA*\n\n"
        "🚀 *INSPEKSI*\n"
        "`/inspeksi unit X user Y` - Jalankan inspeksi\n"
        "`/inspeksi unit X user Y test` - Test mode\n"
        "`/inspeksi unit X user Y slow` - Slow mode\n"
        "`/inspeksi unit X user Y exceptual 1,2` - Skip titik\n\n"
        "📊 *MONITORING*\n"
        "`/status` - Unit yang sedang berjalan\n"
        "`/log unit X` - Lihat log unit\n"
        "`/log unit X 100` - Lihat 100 line terakhir\n\n"
        "🔧 *MANAGEMENT*\n"
        "`/unit X` - Lihat titik inspeksi unit X\n"
        "`/alluser` - Lihat daftar user\n\n"
        "🛑 *CONTROL*\n"
        "`/kill unit X` - Hentikan unit X\n"
        "`/killall` - Hentikan semua unit\n"
        "`/clearall` - Bersihkan database\n"
        "`/info` - Informasi Sistem\n"
        "`/ping` - Cek bot\n"
        "`/uptime` - lama Bot running\n"
        "`/clean` - Hapus proses mati\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *CONTOH CEPAT:*\n"
        "/inspeksi unit 1 user 7\n"
        "/unit 2\n"
        "/status",
        parse_mode=ParseMode.MARKDOWN
    )

@auth_audit
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cek apakah bot hidup"""
    import time
    start = time.time()
    msg = await update.message.reply_text("🏓 *PONG!*", parse_mode=ParseMode.MARKDOWN)
    end = time.time()
    
    await msg.edit_text(
        f"🏓 *PONG!*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"⏱️ Latency: `{(end-start)*1000:.2f} ms`\n"
        f"📅 Uptime: *Bot Online*",
        parse_mode=ParseMode.MARKDOWN
    )

@auth_audit
async def inspeksi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    
    unit = None
    user = None
    test = ''
    slow = ''
    exceptual = ''
    
    i = 0
    while i < len(args):
        arg = args[i].lower()
        if arg == 'unit' and i+1 < len(args):
            unit = args[i+1]
            i += 1
        elif arg == 'user' and i+1 < len(args):
            user = args[i+1]
            i += 1
        elif arg == 'exceptual' and i+1 < len(args):
            exceptual = f'-exceptual {args[i+1]}'
            i += 1
        elif arg == 'test':
            test = '-unittest'
        elif arg == 'slow':
            slow = '-slow'
        i += 1
    
    if not unit or not user:
        await update.message.reply_text(
            "❌ *Format salah!*\nContoh: `/inspeksi unit 1 user 7`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Cek unit sedang jalan
    if is_unit_running(unit):
        info = get_unit_info(unit)
        if info:
            started = datetime.fromisoformat(info['started'])
            uptime = str(datetime.now() - started).split('.')[0]
            
            await update.message.reply_text(
                f"⚠️ *UNIT {unit} SEDANG DIGUNAKAN!*\n\n"
                f"User: {info['user']}\n"
                f"Uptime: {uptime}\n"
                f"PID: `{info['pid']}`\n\n"
                f"Gunakan `/kill unit {unit}` untuk menghentikan",
                parse_mode=ParseMode.MARKDOWN
            )
        return
    
    # Build command
    command = f'python v25.py -auto -unitElectrical -unit {unit} -user {user} {test} {slow} {exceptual}'
    user_name = update.effective_user.full_name
    chat_id = update.effective_chat.id
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"unit_{unit}_{timestamp}.log")
    
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUNBUFFERED'] = '1'
    
    try:
        log_f = open(log_file, 'w', encoding='utf-8')
        log_f.write(f"=== SHADOW CORE - UNIT {unit} ===\n")
        log_f.write(f"Started: {datetime.now()}\n")
        log_f.write(f"User: {user_name}\n")
        log_f.write(f"Command: {command}\n")
        log_f.write(f"===================================\n\n")
        log_f.flush()
        
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=os.getcwd(),
            start_new_session=True
        )
        
        pid = process.pid
        lock_unit(unit, pid, command, user_name, chat_id, log_file)
        
        await update.message.reply_text(
            f"✅ *INSPEKSI DIMULAI*\n\n"
            f"Unit: {unit}\n"
            f"User ID: {user}\n"
            f"Operator: {user_name}\n"
            f"PID: `{pid}`\n"
            f"Test Mode: {'Ya' if test else 'Tidak'}\n"
            f"Slow Mode: {'Ya' if slow else 'Tidak'}\n\n"
            f"Gunakan:\n"
            f"`/status` - Cek status\n"
            f"`/kill unit {unit}` - Hentikan\n"
            f"`/log unit {unit}` - Lihat log",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ *GAGAL:* `{str(e)}`", parse_mode=ParseMode.MARKDOWN)

@auth_audit
async def alluser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan semua user yang tersedia di user.json"""
    user_file = 'user.json'
    
    if not os.path.exists(user_file):
        await update.message.reply_text(
            "❌ *File user.json tidak ditemukan!*",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        with open(user_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        if not users:
            await update.message.reply_text("ℹ️ Tidak ada user terdaftar.")
            return
        
        response = "*👥 DAFTAR USER TERSEDIA*\n\n"
        response += "```\n"
        response += f"{'No':<4} {'ID':<12} {'Nama'}\n"
        response += "-" * 40 + "\n"
        
        for key, user_data in sorted(users.items(), key=lambda x: int(x[0])):
            user_id = user_data.get('id', '-')
            name = user_data.get('name', '-')
            status = user_data.get('status', '-')
            response += f"{key:<4} {user_id:<12} {name}"
            if status:
                response += f" [{status.upper()}]"
            response += "\n"
        
        response += "```\n"
        response += f"\nTotal: {len(users)} user\n"
        response += "Gunakan `/inspeksi unit X user Y`"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error membaca user.json: `{str(e)}`",
            parse_mode=ParseMode.MARKDOWN
        )

@auth_audit
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    db = clean_dead_processes(db)
    save_db(db)
    
    if not db:
        await update.message.reply_text("ℹ️ *TIDAK ADA UNIT YANG SEDANG BERJALAN*", parse_mode=ParseMode.MARKDOWN)
        return
    
    response = "*🔥 UNIT YANG SEDANG BERJALAN*\n\n"
    
    for unit in sorted(db.keys(), key=int):
        info = db[unit]
        started = datetime.fromisoformat(info['started'])
        uptime = str(datetime.now() - started).split('.')[0]
        
        alive = is_process_alive(info['pid'])
        status_icon = "🟢" if alive else "🔴"
        
        response += f"{status_icon} *UNIT {unit}*\n"
        response += f"   👤 {info['user']}\n"
        response += f"   ⏱ {uptime}\n"
        response += f"   🔢 PID: `{info['pid']}`\n\n"
    
    response += f"Total: {len(db)} unit\n"
    response += "Gunakan `/kill unit X` atau `/clearall`"
    
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

@auth_audit
async def clearall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paksa hapus SEMUA unit dari database"""
    if clear_all_units():
        await update.message.reply_text(
            "✅ *DATABASE DIHAPUS*\n"
            "Semua unit telah dibersihkan dari record.\n"
            "Proses yang sedang berjalan TIDAK dimatikan.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            "ℹ️ Database sudah kosong.",
            parse_mode=ParseMode.MARKDOWN
        )

@auth_audit
async def killall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kill semua unit dengan brutal di Termux"""
    db = load_db()
    
    if not db:
        await update.message.reply_text("ℹ️ Tidak ada unit yang berjalan", parse_mode=ParseMode.MARKDOWN)
        return
    
    killed = []
    failed = []
    
    for unit, info in list(db.items()):
        pid = info['pid']
        try:
            # Brutal kill semua proses terkait unit
            subprocess.run(f"pkill -9 -f 'v25.py.*unit {unit}'", shell=True)
            subprocess.run(f"kill -9 {pid} 2>/dev/null", shell=True)
            
            # Cari dan kill semua child process
            subprocess.run(
                f"ps -o pid= -o ppid= | awk '$2=={pid} {{print $1}}' | xargs -r kill -9",
                shell=True
            )
            
            killed.append(unit)
        except Exception as e:
            failed.append(f"{unit}: {str(e)[:30]}")
        
        # Tetap unlock
        unlock_unit(unit)
    
    # Wait sebentar
    await asyncio.sleep(1)
    
    # Clean database
    db = clean_dead_processes(db)
    save_db(db)
    
    response = f"🔪 *KILLALL EXECUTED*\n"
    response += f"✅ Killed: {', '.join(killed) if killed else 'none'}\n"
    if failed:
        response += f"❌ Failed: {', '.join(failed)}"
    
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
"""
@auth_audit
async def kill_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "❌ *Format:* `/kill unit 1` atau `/killall`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if args[0].lower() == 'unit' and len(args) > 1:
        unit = args[1]
        info = get_unit_info(unit)
        
        if not info:
            # Coba tetap bersihkan database
            db = load_db()
            if str(unit) in db:
                del db[str(unit)]
                save_db(db)
            await update.message.reply_text(
                f"ℹ️ Unit {unit} tidak ditemukan, database dibersihkan",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        pid = info['pid']
        
        try:
            # Coba kill proses
            killed = False
            if HAS_PSUTIL:
                try:
                    parent = psutil.Process(pid)
                    for child in parent.children(recursive=True):
                        child.kill()
                    parent.kill()
                    killed = True
                except psutil.NoSuchProcess:
                    pass
            else:
                result = subprocess.run(f"kill -9 {pid} 2>/dev/null", shell=True)
                killed = result.returncode == 0
            
            # 🔥 PENTING: Selalu unlock
            unlock_unit(unit)
            
            if killed:
                await update.message.reply_text(
                    f"✅ *UNIT {unit} DIHENTIKAN*\nPID: `{pid}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    f"ℹ️ Unit {unit} sudah tidak berjalan, database dibersihkan",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            # Paksa unlock
            unlock_unit(unit)
            await update.message.reply_text(
                f"⚠️ Unit {unit} dibersihkan dari database\n`{str(e)[:100]}`",
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await update.message.reply_text(
            "❌ Format salah! Gunakan `/kill unit 1` atau `/killall`",
            parse_mode=ParseMode.MARKDOWN
        )
"""
# ===== AUDIT LOG FUNCTIONS =====
def audit_log(user_id, user_name, command, args, result=""):
    """Catat semua aktivitas user ke audit.log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] USER: {user_id} ({user_name}) | CMD: /{command} {args} | RESULT: {result}\n"
    
    try:
        with open(AUDIT_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        logger.error(f"Gagal menulis audit log: {e}")
    
    return log_entry

def get_last_commands(limit=10):
    """Ambil N command terakhir dari audit log"""
    if not os.path.exists(AUDIT_LOG_FILE):
        return []
    
    try:
        with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Ambil last N lines (balik, ambil, balik lagi)
        last_lines = lines[-limit:] if len(lines) > limit else lines
        return last_lines
    except Exception as e:
        return [f"Error membaca log: {e}"]

# ===== AUDIT DECORATOR =====
def audited(func):
    """Decorator untuk mencatat semua command yang dijalankan"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_name = update.effective_user.full_name or update.effective_user.username or str(user_id)
        
        # Dapatkan command dan args
        command = func.__name__.replace('_command', '')
        args = ' '.join(context.args) if context.args else ''
        
        # Cek auth dulu
        if ALLOWED_USERS and user_id not in ALLOWED_USERS:
            await update.message.reply_text("❌ Akses ditolak!")
            audit_log(user_id, user_name, command, args, "ACCESS DENIED")
            return
        
        # Jalankan fungsi asli
        try:
            result = await func(update, context)
            audit_log(user_id, user_name, command, args, "SUCCESS")
            return result
        except Exception as e:
            audit_log(user_id, user_name, command, args, f"ERROR: {str(e)[:50]}")
            raise
    
    return wrapper

def get_last_command_by_user(user_id, limit=1):
    """Ambil command terakhir dari user tertentu"""
    if not os.path.exists(AUDIT_LOG_FILE):
        return []
    
    try:
        with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Filter berdasarkan user_id, ambil dari bawah
        filtered = []
        for line in reversed(lines):
            if f"USER: {user_id}" in line:
                filtered.append(line.strip())
                if len(filtered) >= limit:
                    break
        
        return filtered
    except Exception as e:
        return [f"Error: {e}"]

async def last_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lihat command terakhir yang dijalankan"""
    args = context.args
    
    if args and args[0].isdigit():
        # Cari berdasarkan user ID
        user_id = int(args[0])
        history = get_last_command_by_user(user_id, limit=5)
        if history:
            response = f"📋 *COMMAND TERAKHIR USER {user_id}*\n\n```\n"
            response += '\n'.join(history)
            response += "\n```"
        else:
            response = f"ℹ️ Tidak ada history untuk user {user_id}"
    else:
        # Tampilkan 10 command terakhir semua user
        history = get_last_commands(limit=10)
        if history:
            response = "📋 *10 COMMAND TERAKHIR*\n\n```\n"
            response += ''.join(history)
            response += "\n```"
        else:
            response = "ℹ️ Belum ada aktivitas tercatat"
    
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

async def last_command_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lihat siapa yang terakhir menjalankan command dan apa"""
    history = get_last_commands(limit=1)
    if history:
        await update.message.reply_text(
            f"🔍 *USER TERAKHIR AKTIF*\n\n```\n{history[0].strip()}\n```",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("ℹ️ Belum ada aktivitas")

@auth_audit
async def kill_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "❌ *Format:* `/kill unit 1` atau `/killall`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if args[0].lower() == 'unit' and len(args) > 1:
        unit = args[1]
        info = get_unit_info(unit)
        
        if not info:
            db = load_db()
            if str(unit) in db:
                del db[str(unit)]
                save_db(db)
            await update.message.reply_text(
                f"ℹ️ Unit {unit} tidak ditemukan, database dibersihkan",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        pid = info['pid']
        killed = False
        
        try:
            # ===== TERMUX-SPECIFIC KILL =====
            # 1. Cari semua process yang terkait dengan unit ini
            import subprocess
            import signal
            
            # Dapatkan semua PID dari process tree
            pids_to_kill = [pid]
            
            # Cari child processes menggunakan ps
            try:
                # Cari semua proses dengan parent PID ini
                result = subprocess.run(
                    f"ps -o pid= -o ppid= | awk '$2=={pid} {{print $1}}'",
                    shell=True, capture_output=True, text=True
                )
                child_pids = [int(p.strip()) for p in result.stdout.split() if p.strip().isdigit()]
                pids_to_kill.extend(child_pids)
                
                # Cari juga proses v25.py dengan unit ini
                result2 = subprocess.run(
                    f"ps -o pid= -o args= | grep -E 'v25.py.*unit {unit}' | awk '{{print $1}}'",
                    shell=True, capture_output=True, text=True
                )
                grep_pids = [int(p.strip()) for p in result2.stdout.split() if p.strip().isdigit()]
                pids_to_kill.extend(grep_pids)
            except Exception:
                pass
            
            # Hapus duplikat
            pids_to_kill = list(set(pids_to_kill))
            
            # 2. Kill semua dengan SIGKILL (9)
            for p in pids_to_kill:
                try:
                    os.kill(p, signal.SIGKILL)
                    killed = True
                except (ProcessLookupError, OSError):
                    pass
            
            # 3. Fallback: pkill berdasarkan command
            if not killed:
                subprocess.run(f"pkill -9 -f 'v25.py.*unit {unit}'", shell=True)
                subprocess.run(f"pkill -9 -f 'python.*v25.py.*{unit}'", shell=True)
                subprocess.run(f"kill -9 {pid} 2>/dev/null", shell=True)
                killed = True
            
            # 4. Tunggu sebentar dan verifikasi
            await asyncio.sleep(1)
            
            # 5. VERIFIKASI: cek apakah masih ada proses dengan unit ini
            check = subprocess.run(
                f"ps -o args= | grep -E 'v25.py.*unit {unit}' | grep -v grep",
                shell=True, capture_output=True, text=True
            )
            
            if check.stdout.strip():
                # Masih ada! Paksa dengan cara brutal
                subprocess.run(
                    f"ps -o pid= -o args= | grep -E 'v25.py.*unit {unit}' | awk '{{print $1}}' | xargs -r kill -9",
                    shell=True
                )
                await asyncio.sleep(0.5)
            
            # ===== UNLOCK =====
            unlock_unit(unit)
            
            # Cek apakah proses benar-benar mati
            try:
                os.kill(pid, 0)
                status = "⚠️ *MUNGKIN MASIH BERJALAN* - Cek `/status`"
            except (ProcessLookupError, OSError):
                status = "✅ *BERHASIL DIHENTIKAN*"
            
            await update.message.reply_text(
                f"🔪 *UNIT {unit} DIKILL*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🔢 PID: `{pid}`\n"
                f"📊 PID yang di-kill: {len(pids_to_kill)}\n"
                f"🛑 Status: {status}",
                parse_mode=ParseMode.MARKDOWN
            )
                
        except Exception as e:
            # Paksa unlock & bersihkan
            unlock_unit(unit)
            # Paksa kill semua proses terkait
            subprocess.run(f"pkill -9 -f 'v25.py.*unit {unit}'", shell=True)
            subprocess.run(f"kill -9 {pid} 2>/dev/null", shell=True)
            
            await update.message.reply_text(
                f"⚠️ Unit {unit} dibersihkan paksa\n"
                f"Error: `{str(e)[:100]}`",
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await update.message.reply_text(
            "❌ Format salah! Gunakan `/kill unit 1` atau `/killall`",
            parse_mode=ParseMode.MARKDOWN
        )
        
@auth_audit
async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    
    if len(args) < 2 or args[0].lower() != 'unit':
        await update.message.reply_text("❌ *Format:* `/log unit 1`", parse_mode=ParseMode.MARKDOWN)
        return
    
    unit = args[1]
    lines = int(args[2]) if len(args) > 2 else 50
    
    info = get_unit_info(unit)
    
    if not info:
        await update.message.reply_text(f"ℹ️ Unit {unit} tidak ditemukan", parse_mode=ParseMode.MARKDOWN)
        return
    
    log_file = info['log_file']
    
    if not os.path.exists(log_file):
        await update.message.reply_text(f"❌ File log tidak ditemukan", parse_mode=ParseMode.MARKDOWN)
        return
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()
        
        last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        log_text = ''.join(last_lines)
        
        if not log_text.strip():
            await update.message.reply_text(f"ℹ️ Log Unit {unit} kosong")
            return
        
        if len(log_text) > 3500:
            temp_file = f"temp_log_unit_{unit}.txt"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(log_text)
            
            with open(temp_file, 'rb') as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename=f"unit_{unit}_log.txt",
                    caption=f"📄 Log Unit {unit}"
                )
            
            os.remove(temp_file)
        else:
            await update.message.reply_text(
                f"📄 *LOG UNIT {unit}*\n\n```\n{log_text[:3500]}\n```",
                parse_mode=ParseMode.MARKDOWN
            )
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: `{str(e)}`", parse_mode=ParseMode.MARKDOWN)

@auth_audit
async def clean_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    old = len(db)
    db = clean_dead_processes(db)
    new = len(db)
    save_db(db)
    
    await update.message.reply_text(
        f"🧹 *CLEANED*\nDihapus: {old - new}\nTersisa: {new}",
        parse_mode=ParseMode.MARKDOWN
    )
@auth_audit
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan info sistem"""
    import platform
    import psutil
    
    # CPU & Memory
    cpu_percent = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    
    # Disk
    disk = psutil.disk_usage(os.getcwd())
    
    # Python version
    py_ver = sys.version.split()[0]
    
    response = (
        f"🖥️ *SYSTEM INFO*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💻 *OS:* `{platform.system()} {platform.release()}`\n"
        f"🐍 *Python:* `{py_ver}`\n"
        f"📁 *CWD:* `{os.getcwd()}`\n\n"
        f"⚡ *CPU:* `{cpu_percent}%`\n"
        f"🧠 *RAM:* `{mem.percent}%` ({mem.used//1024**2}MB / {mem.total//1024**2}MB)\n"
        f"💾 *DISK:* `{disk.percent}%` ({disk.free//1024**2}MB free)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 *Bot Status:* ONLINE"
    )
    
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

# Di bagian atas, tambahin variable global
BOT_START_TIME = datetime.now()

@auth_audit
async def uptime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan uptime bot"""
    uptime = datetime.now() - BOT_START_TIME
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s" if days > 0 else f"{hours}h {minutes}m {seconds}s"
    
    await update.message.reply_text(
        f"⏱️ *BOT UPTIME*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🟢 Online sejak: `{BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S')}`\n"
        f"⏳ Uptime: `{uptime_str}`",
        parse_mode=ParseMode.MARKDOWN
    )
# ===== MAIN =====
if __name__ == "__main__":
    print("="*50)
    print("SHADOW BOT V4 - ASYNC (FIXED)")
    print("="*50)
    
    # Build application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("inspeksi", inspeksi_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("kill", kill_command))
    app.add_handler(CommandHandler("killall", killall_command))
    app.add_handler(CommandHandler("log", log_command))
    app.add_handler(CommandHandler("clearall", clearall_command))
    app.add_handler(CommandHandler("clean", clean_command))
    app.add_handler(CommandHandler("unit", unit_command))
    app.add_handler(CommandHandler("alluser", alluser_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("uptime", uptime_command))
    app.add_handler(CommandHandler("info", info_command))
    app.add_handler(CommandHandler("last", last_command))
    app.add_handler(CommandHandler("lastuser", last_command_user))
    # Clean on startup
    db = load_db()
    db = clean_dead_processes(db)
    save_db(db)
    print(f"Loaded {len(db)} active units")
    
    print("Bot running... Ctrl+C to stop")
    
    # Jalankan bot
    app.run_polling()