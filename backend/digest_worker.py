"""Run the in-app daily literature delivery independently of browser sessions."""
import os
import signal
import threading
from pathlib import Path
from accounts import Accounts
from daily_digest import DigestEngine

def main():
    stop=threading.Event()
    for sig in (signal.SIGINT,signal.SIGTERM):
        signal.signal(sig,lambda *_:stop.set())
    configured=os.getenv('RESEARCHLENS_DB_PATH', '').strip()
    db=(Path(configured).expanduser() if configured else Path(__file__).resolve().parent/'papers.db').resolve()
    Accounts(db)
    engine=DigestEngine(db)
    print('ResearchLens daily digest worker started (Asia/Shanghai 09:00).',flush=True)
    while not stop.is_set():
        try:engine.run_due()
        except Exception:print('Digest scheduler temporarily unavailable; will retry.',flush=True)
        stop.wait(30)

if __name__=='__main__':main()
