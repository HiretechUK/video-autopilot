#!/bin/bash
# One-time setup of the TikTok poster on the VPS. Run as root:
#   curl -sSL https://raw.githubusercontent.com/HiretechUK/video-autopilot/main/vps/setup.sh | bash
set -e
D=/opt/ttposter
mkdir -p $D/www && cd $D
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv xvfb fonts-noto-color-emoji curl >/dev/null
[ -d venv ] || python3 -m venv venv
venv/bin/pip install -q --upgrade pip playwright requests
venv/bin/python -m playwright install --with-deps chromium >/dev/null
curl -sSL -o ttposter.py https://raw.githubusercontent.com/HiretechUK/video-autopilot/main/vps/ttposter.py
[ -f posted.json ] || echo '{"IY-01": {"link": "posted by hand", "at": "2026-10-30"}}' > posted.json
cat > run.sh <<'R'
#!/bin/bash
cd /opt/ttposter
curl -sSL -o ttposter.py.new https://raw.githubusercontent.com/HiretechUK/video-autopilot/main/vps/ttposter.py && mv ttposter.py.new ttposter.py
xvfb-run -a --server-args="-screen 0 1366x900x24" venv/bin/python ttposter.py "$@"
R
chmod +x run.sh
( crontab -l 2>/dev/null | grep -v ttposter ; echo "47 18 * * * /opt/ttposter/run.sh run >> /opt/ttposter/log.txt 2>&1" ) | crontab -
ufw allow 8088/tcp >/dev/null 2>&1 || true
echo "SETUP DONE"
