#!/usr/bin/env python3

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

BOT_TOKEN = "8319020434:AAHM1hNMZJo3DjeHBUNfg5WkL7OWVgd15dk"
ALLOWED_USERS = []
AUDIT_LOG_FILE = "audit.log"
PROCESS_DB = "unit_processes.json"
LOG_DIR = "logs"
TERMUX_FULL_ACCESS = True
TERMUX_COMMAND_TIMEOUT = 60
TERMUX_LONG_TIMEOUT = 300
BOT_START_TIME = datetime.now()

os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

try:
    import psutil
    HAS_PSUTIL = True
    logger.info("✓ psutil loaded")
except ImportError:
    HAS_PSUTIL = False
    logger.warning("⚠️ psutil not found")

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
    if os.path.exists(PROCESS_DB):
        os.remove(PROCESS_DB)
        return True
    return False

def audit_log(user_id, user_name, command, args, result=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] USER: {user_id} ({user_name}) | CMD: /{command} {args} | RESULT: {result}\n"
    try:
        with open(AUDIT_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        logger.error(f"Gagal menulis audit log: {e}")
    return log_entry

def get_last_commands(limit=10):
    if not os.path.exists(AUDIT_LOG_FILE):
        return []
    try:
        with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        last_lines = lines[-limit:] if len(lines) > limit else lines
        return last_lines
    except Exception as e:
        return [f"Error membaca log: {e}"]

def get_last_command_by_user(user_id, limit=1):
    if not os.path.exists(AUDIT_LOG_FILE):
        return []
    try:
        with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        filtered = []
        for line in reversed(lines):
            if f"USER: {user_id}" in line:
                filtered.append(line.strip())
                if len(filtered) >= limit:
                    break
        return filtered
    except Exception as e:
        return [f"Error: {e}"]

def auth_audit(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_name = update.effective_user.full_name or update.effective_user.username or str(user_id)
        command = func.__name__.replace('_command', '')
        args = ' '.join(context.args) if context.args else ''
        if ALLOWED_USERS and user_id not in ALLOWED_USERS:
            await update.message.reply_text("❌ Akses ditolak!")
            audit_log(user_id, user_name, command, args, "ACCESS DENIED")
            return
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
        """```                 
┏┓┳┳┏┓┓┏┓
┣ ┃┃┃ ┃┫ 
┻ ┗┛┗┛┛┗┛
┓┏┏┓┓ ┓ ┓┏┏┓┓┏┏┓
┣┫┃┃┃ ┃ ┗┫┗┓┗┫┗┓
┛┗┗┛┗┛┗┛┗┛┗┛┗┛┗┛                                                                   
                                                    
        ```"""
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
        "`/clean` - Hapus proses mati\n"
        "💻 *TERMUX FULL CONTROL*\n"
        "`/exec command` - Jalankan command (full access)\n"
        "`/exlong command` - Timeout 5 menit\n"
        "`/execbg command` - Background execution\n"
        "`/tstatus` - Status Termux lengkap\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *CONTOH CEPAT:*\n"
        "/inspeksi unit 1 user 7\n"
        "/unit 2\n"
        "/status",
        parse_mode=ParseMode.MARKDOWN
    )

@auth_audit
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            """``` 
┏┓┳┳┏┓┓┏┓
┣ ┃┃┃ ┃┫ 
┻ ┗┛┗┛┛┗┛
┓┏┏┓┓ ┓ ┓┏┏┓┓┏┏┓
┣┫┃┃┃ ┃ ┗┫┗┓┗┫┗┓
┛┗┗┛┗┛┗┛┗┛┗┛┗┛┗┛  
            ``` """
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
    db = load_db()
    if not db:
        await update.message.reply_text("ℹ️ Tidak ada unit yang berjalan", parse_mode=ParseMode.MARKDOWN)
        return
    killed = []
    failed = []
    for unit, info in list(db.items()):
        pid = info['pid']
        try:
            subprocess.run(f"pkill -9 -f 'v25.py.*unit {unit}'", shell=True)
            subprocess.run(f"kill -9 {pid} 2>/dev/null", shell=True)
            subprocess.run(
                f"ps -o pid= -o ppid= | awk '$2=={pid} {{print $1}}' | xargs -r kill -9",
                shell=True
            )
            killed.append(unit)
        except Exception as e:
            failed.append(f"{unit}: {str(e)[:30]}")
        unlock_unit(unit)
    await asyncio.sleep(1)
    db = clean_dead_processes(db)
    save_db(db)
    response = f"🔪 *KILLALL EXECUTED*\n"
    response += f"✅ Killed: {', '.join(killed) if killed else 'none'}\n"
    if failed:
        response += f"❌ Failed: {', '.join(failed)}"
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

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
            import signal
            pids_to_kill = [pid]
            try:
                result = subprocess.run(
                    f"ps -o pid= -o ppid= | awk '$2=={pid} {{print $1}}'",
                    shell=True, capture_output=True, text=True
                )
                child_pids = [int(p.strip()) for p in result.stdout.split() if p.strip().isdigit()]
                pids_to_kill.extend(child_pids)
                result2 = subprocess.run(
                    f"ps -o pid= -o args= | grep -E 'v25.py.*unit {unit}' | awk '{{print $1}}'",
                    shell=True, capture_output=True, text=True
                )
                grep_pids = [int(p.strip()) for p in result2.stdout.split() if p.strip().isdigit()]
                pids_to_kill.extend(grep_pids)
            except Exception:
                pass
            pids_to_kill = list(set(pids_to_kill))
            for p in pids_to_kill:
                try:
                    os.kill(p, signal.SIGKILL)
                    killed = True
                except (ProcessLookupError, OSError):
                    pass
            if not killed:
                subprocess.run(f"pkill -9 -f 'v25.py.*unit {unit}'", shell=True)
                subprocess.run(f"pkill -9 -f 'python.*v25.py.*{unit}'", shell=True)
                subprocess.run(f"kill -9 {pid} 2>/dev/null", shell=True)
                killed = True
            await asyncio.sleep(1)
            check = subprocess.run(
                f"ps -o args= | grep -E 'v25.py.*unit {unit}' | grep -v grep",
                shell=True, capture_output=True, text=True
            )
            if check.stdout.strip():
                subprocess.run(
                    f"ps -o pid= -o args= | grep -E 'v25.py.*unit {unit}' | awk '{{print $1}}' | xargs -r kill -9",
                    shell=True
                )
                await asyncio.sleep(0.5)
            unlock_unit(unit)
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
            unlock_unit(unit)
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
    import platform
    import psutil
    cpu_percent = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(os.getcwd())
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

@auth_audit
async def uptime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def last_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args and args[0].isdigit():
        user_id = int(args[0])
        history = get_last_command_by_user(user_id, limit=5)
        if history:
            response = f"📋 *COMMAND TERAKHIR USER {user_id}*\n\n```\n"
            response += '\n'.join(history)
            response += "\n```"
        else:
            response = f"ℹ️ Tidak ada history untuk user {user_id}"
    else:
        history = get_last_commands(limit=10)
        if history:
            response = "📋 *10 COMMAND TERAKHIR*\n\n```\n"
            response += ''.join(history)
            response += "\n```"
        else:
            response = "ℹ️ Belum ada aktivitas tercatat"
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

async def last_command_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    history = get_last_commands(limit=1)
    if history:
        await update.message.reply_text(
            f"🔍 *USER TERAKHIR AKTIF*\n\n```\n{history[0].strip()}\n```",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("ℹ️ Belum ada aktivitas")

async def exec_termux_full(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str, timeout: int = 60):
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name or str(user_id)
    audit_log(user_id, user_name, 'termux', command, 'EXECUTING')
    msg = await update.message.reply_text(
        f"🔥 *TERMUX FULL ACCESS*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 Command: `{command}`\n"
        f"⏳ *Executing...*",
        parse_mode=ParseMode.MARKDOWN
    )
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.getcwd()
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            try:
                process.kill()
                if process.pid:
                    os.kill(process.pid, 9)
            except:
                pass
            await msg.edit_text(
                f"⏰ *TIMEOUT!*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📌 Command: `{command}`\n"
                f"⏱️ Timeout: `{timeout}s`\n\n"
                f"⚠️ Proses telah di-kill paksa.",
                parse_mode=ParseMode.MARKDOWN
            )
            audit_log(user_id, user_name, 'termux', command, 'TIMEOUT')
            return
        output = stdout.decode('utf-8', errors='replace')
        error = stderr.decode('utf-8', errors='replace')
        response = f"💻 *TERMUX FULL ACCESS*\n"
        response += f"━━━━━━━━━━━━━━━━━━\n"
        response += f"📌 Command: `{command}`\n"
        response += f"📊 Exit Code: `{process.returncode}`\n"
        response += f"⏱️ Time: `{timeout}s`\n\n"
        if output.strip():
            response += f"📤 *OUTPUT:*\n"
            response += f"```\n{output.strip()[:3500]}\n```\n"
        if error.strip():
            response += f"⚠️ *STDERR:*\n"
            response += f"```\n{error.strip()[:1500]}\n```\n"
        if not output.strip() and not error.strip():
            response += "ℹ️ *No output (empty)*\n"
        if len(response) > 4000:
            temp_file = f"temp_termux_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            full_output = f"Command: {command}\n\nSTDOUT:\n{output}\n\nSTDERR:\n{error}"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(full_output)
            with open(temp_file, 'rb') as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename=f"termux_output.txt",
                    caption=f"💻 Output untuk: `{command[:50]}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            os.remove(temp_file)
            await msg.delete()
            audit_log(user_id, user_name, 'termux', command, 'SUCCESS (file)')
        else:
            await msg.edit_text(response, parse_mode=ParseMode.MARKDOWN)
            audit_log(user_id, user_name, 'termux', command, 'SUCCESS')
    except Exception as e:
        await msg.edit_text(
            f"❌ *ERROR EXECUTING*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📌 Command: `{command}`\n"
            f"⚠️ Error: `{str(e)[:200]}`",
            parse_mode=ParseMode.MARKDOWN
        )
        audit_log(user_id, user_name, 'termux', command, f'ERROR: {str(e)[:50]}')

@auth_audit
async def exec_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "🔥 *TERMUX FULL ACCESS*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "📌 *Format:* `/exec <command>`\n"
            "📌 *Contoh:* `/exec ls -la`\n"
            "📌 *Contoh:* `/exec python v25.py -status`\n"
            "📌 *Contoh:* `/exec rm -rf folder`\n"
            "📌 *Contoh:* `/exec termux-wifi-enable`\n\n"
            "⚡ *FULL ACCESS - NO RESTRICTIONS*\n"
            "⏱️ *Timeout:* 60 detik\n"
            "⏰ *Long timeout:* `/exlong` (300 detik)\n\n"
            "⚠️ *Anda bertanggung jawab atas semua command!*",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    command = ' '.join(args)
    await exec_termux_full(update, context, command, timeout=TERMUX_COMMAND_TIMEOUT)

@auth_audit
async def exec_long_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "⏰ *LONG EXECUTION*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Format: `/exlong <command>`\n"
            "Timeout: 300 detik (5 menit)\n\n"
            "Contoh: `/exlong python v25.py -auto -unit 1 -user 7`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    command = ' '.join(args)
    await exec_termux_full(update, context, command, timeout=TERMUX_LONG_TIMEOUT)

@auth_audit
async def exec_background_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "🔄 *BACKGROUND EXECUTION*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Format: `/execbg <command>`\n"
            "Command berjalan di background\n"
            "Tidak menunggu output\n\n"
            "Contoh: `/execbg python v25.py -auto -unit 1 -user 7`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    command = ' '.join(args)
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name or str(user_id)
    audit_log(user_id, user_name, 'termux-bg', command, 'BACKGROUND')
    try:
        bg_command = f"nohup {command} > /dev/null 2>&1 &"
        process = await asyncio.create_subprocess_shell(
            bg_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.getcwd()
        )
        await update.message.reply_text(
            f"🔄 *BACKGROUND EXECUTION STARTED*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📌 Command: `{command}`\n"
            f"🔢 PID: `{process.pid}`\n\n"
            f"✅ Proses berjalan di background",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ *GAGAL BG EXECUTION*\n"
            f"Error: `{str(e)[:100]}`",
            parse_mode=ParseMode.MARKDOWN
        )

@auth_audit
async def termux_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import platform
    ps_output = subprocess.run(
        "ps aux | head -20",
        shell=True, capture_output=True, text=True
    ).stdout
    df_output = subprocess.run(
        "df -h",
        shell=True, capture_output=True, text=True
    ).stdout
    mem_output = subprocess.run(
        "free -h",
        shell=True, capture_output=True, text=True
    ).stdout
    response = f"📱 *TERMUX FULL STATUS*\n"
    response += f"━━━━━━━━━━━━━━━━━━\n\n"
    response += f"📂 *CWD:* `{os.getcwd()}`\n"
    response += f"🐍 *Python:* `{sys.version.split()[0]}`\n"
    response += f"🖥️ *Platform:* `{platform.system()}`\n"
    response += f"👤 *User:* `{os.environ.get('USER', 'unknown')}`\n"
    response += f"📅 *Time:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
    response += f"📁 *Files:* `{len(os.listdir('.'))}` files\n\n"
    response += f"💾 *Disk:*\n```\n{df_output.strip()}\n```\n"
    response += f"🧠 *Memory:*\n```\n{mem_output.strip()}\n```\n"
    response += f"📊 *Top Processes:*\n```\n{ps_output.strip()}\n```"
    if len(response) > 4000:
        temp_file = f"temp_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(response)
        with open(temp_file, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                filename=f"termux_status.txt",
                caption="📱 Termux Full Status"
            )
        os.remove(temp_file)
    else:
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

if __name__ == "__main__":
    print("="*50)
    print("STANLEY BOT - FUCK HOLLYSYS")
    print("="*50)
    app = Application.builder().token(BOT_TOKEN).build()
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
    app.add_handler(CommandHandler("exec", exec_command))
    app.add_handler(CommandHandler("exlong", exec_long_command))
    app.add_handler(CommandHandler("execbg", exec_background_command))
    app.add_handler(CommandHandler("tstatus", termux_status_command))
    app.add_handler(CommandHandler("termux", termux_status_command))
    db = load_db()
    db = clean_dead_processes(db)
    save_db(db)
    print(f"Loaded {len(db)} active units")
    print("Bot running... Ctrl+C to stop")
    app.run_polling()