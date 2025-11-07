# TradeBot Deployment Guide

This guide provides instructions for deploying TradeBot in different environments.

## ⚠️ Pre-Deployment Checklist

Before deploying to production:

- [ ] All tests pass (80%+ coverage achieved)
- [ ] Security audit completed
- [ ] Extensive paper trading validation (minimum 3 months)
- [ ] Risk management parameters reviewed
- [ ] Compliance with SEBI regulations confirmed
- [ ] Backup and recovery procedures established
- [ ] Monitoring and alerting configured
- [ ] API rate limits understood and handled
- [ ] Circuit breakers and fail-safes implemented

**DO NOT deploy to production without completing this checklist!**

## Development Environment

### Local Development Setup

1. **Clone and Install**
   ```bash
   git clone https://github.com/mohitkum4r/TradeBot.git
   cd TradeBot
   poetry install --no-root
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your development credentials
   ```

3. **Run in Paper Mode**
   ```bash
   poetry shell
   python main.py
   ```

### Development Best Practices

- Always use `MODE=PAPER` for development
- Use small `INITIAL_CAPITAL` values
- Test with limited stock universe
- Enable debug logging
- Monitor all trades closely

## Testing Environment

### Setting Up Test Environment

1. **Create Test Configuration**
   ```bash
   cp .env.example .env.test
   ```

2. **Configure Test Parameters**
   ```bash
   # .env.test
   MODE=PAPER
   INITIAL_CAPITAL=10000.0
   MAX_EXPOSURE_PER_TRADE=0.1
   RISK_PER_TRADE=0.005
   STOCKS=RELIANCE,TCS  # Limited universe
   POLL_INTERVAL_SECONDS=300  # 5 minutes
   ```

3. **Run Tests**
   ```bash
   poetry run pytest
   ENV_FILE=.env.test python main.py
   ```

## Staging Environment

### Purpose
- Final validation before production
- Real market data but paper trading
- Production-like configuration
- Extended testing period (weeks/months)

### Setup

1. **Server Requirements**
   - Ubuntu 20.04+ or similar Linux distribution
   - Python 3.12+
   - 2GB RAM minimum
   - 10GB disk space
   - Stable internet connection

2. **Install Dependencies**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Python 3.12
   sudo apt install python3.12 python3.12-venv python3-pip
   
   # Install Poetry
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Deploy Application**
   ```bash
   # Clone repository
   git clone https://github.com/mohitkum4r/TradeBot.git
   cd TradeBot
   
   # Install dependencies
   poetry install --no-root --no-dev
   
   # Configure environment
   cp .env.example .env
   # Edit .env with staging configuration
   ```

4. **Configure as Service**
   ```bash
   sudo nano /etc/systemd/system/tradebot-staging.service
   ```
   
   Add:
   ```ini
   [Unit]
   Description=TradeBot Staging Service
   After=network.target
   
   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/TradeBot
   Environment="PATH=/home/ubuntu/.local/bin"
   ExecStart=/home/ubuntu/.local/bin/poetry run python main.py
   Restart=on-failure
   RestartSec=10
   StandardOutput=append:/var/log/tradebot/output.log
   StandardError=append:/var/log/tradebot/error.log
   
   [Install]
   WantedBy=multi-user.target
   ```
   
   Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable tradebot-staging
   sudo systemctl start tradebot-staging
   ```

5. **Monitor Logs**
   ```bash
   # Real-time logs
   sudo journalctl -u tradebot-staging -f
   
   # Application logs
   tail -f /var/log/tradebot/output.log
   ```

## Production Environment

### ⚠️ CRITICAL: Production Deployment Warnings

**ONLY proceed with production deployment if:**
1. Staging has run successfully for minimum 3 months
2. All tests pass with 80%+ coverage
3. Security audit completed and vulnerabilities addressed
4. Risk management thoroughly validated
5. You understand and accept the financial risks

### Production Server Setup

1. **Server Specifications**
   - Ubuntu 22.04 LTS (recommended)
   - Minimum 4GB RAM
   - 50GB SSD storage
   - Dedicated server (not shared)
   - Geographic proximity to exchange (low latency)

2. **Security Hardening**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Configure firewall
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow ssh
   sudo ufw enable
   
   # Disable root login
   sudo nano /etc/ssh/sshd_config
   # Set: PermitRootLogin no
   sudo systemctl restart sshd
   
   # Install fail2ban
   sudo apt install fail2ban
   sudo systemctl enable fail2ban
   sudo systemctl start fail2ban
   ```

3. **Install Application**
   ```bash
   # Create dedicated user
   sudo useradd -m -s /bin/bash tradebot
   sudo su - tradebot
   
   # Clone and setup
   git clone https://github.com/mohitkum4r/TradeBot.git
   cd TradeBot
   poetry install --no-root --no-dev
   ```

4. **Secure Configuration**
   ```bash
   # Create secure .env
   cp .env.example .env
   chmod 600 .env
   
   # Edit with production values
   nano .env
   ```
   
   **Production .env settings**:
   ```bash
   MODE=LIVE  # ⚠️ REAL MONEY
   INITIAL_CAPITAL=50000.0  # Start small!
   MAX_EXPOSURE_PER_TRADE=0.15
   RISK_PER_TRADE=0.01
   STOP_LOSS_PCT=0.03
   TAKE_PROFIT_PCT=0.08
   POLL_INTERVAL_SECONDS=600  # 10 minutes
   ```

5. **Database Backup**
   ```bash
   # Create backup script
   nano ~/backup_db.sh
   ```
   
   Add:
   ```bash
   #!/bin/bash
   DATE=$(date +%Y%m%d_%H%M%S)
   DB_FILE="/home/tradebot/TradeBot/autotrade.db"
   BACKUP_DIR="/home/tradebot/backups"
   
   mkdir -p $BACKUP_DIR
   cp $DB_FILE $BACKUP_DIR/autotrade_$DATE.db
   
   # Keep only last 30 backups
   ls -t $BACKUP_DIR/autotrade_*.db | tail -n +31 | xargs rm -f
   ```
   
   Schedule:
   ```bash
   chmod +x ~/backup_db.sh
   crontab -e
   # Add: 0 */6 * * * /home/tradebot/backup_db.sh
   ```

6. **Configure Production Service**
   ```bash
   sudo nano /etc/systemd/system/tradebot.service
   ```
   
   Add:
   ```ini
   [Unit]
   Description=TradeBot Production Service
   After=network.target
   
   [Service]
   Type=simple
   User=tradebot
   WorkingDirectory=/home/tradebot/TradeBot
   Environment="PATH=/home/tradebot/.local/bin"
   ExecStart=/home/tradebot/.local/bin/poetry run python main.py
   Restart=on-failure
   RestartSec=30
   StandardOutput=append:/var/log/tradebot/output.log
   StandardError=append:/var/log/tradebot/error.log
   
   # Security restrictions
   NoNewPrivileges=true
   PrivateTmp=true
   ProtectSystem=strict
   ProtectHome=true
   ReadWritePaths=/home/tradebot/TradeBot
   
   [Install]
   WantedBy=multi-user.target
   ```
   
   Enable:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable tradebot
   ```

7. **Start Production (With Extreme Caution)**
   ```bash
   # Double-check configuration
   cat .env | grep MODE  # Should show MODE=LIVE
   
   # Start service
   sudo systemctl start tradebot
   
   # Monitor immediately
   sudo journalctl -u tradebot -f
   ```

## Docker Deployment (Recommended)

### Build Docker Image

Create `Dockerfile`:
```dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml poetry.lock ./
COPY . .

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-dev --no-interaction --no-ansi

# Create logs directory
RUN mkdir -p /app/logs

# Run the application
CMD ["python", "main.py"]
```

### Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  tradebot:
    build: .
    container_name: tradebot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./autotrade.db:/app/autotrade.db
      - ./logs:/app/logs
      - ./backups:/app/backups
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Deploy with Docker

```bash
# Build image
docker-compose build

# Run in paper mode first
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Monitoring and Alerting

### Log Monitoring

1. **Configure Log Rotation**
   ```bash
   sudo nano /etc/logrotate.d/tradebot
   ```
   
   Add:
   ```
   /var/log/tradebot/*.log {
       daily
       rotate 30
       compress
       delaycompress
       notifempty
       create 0644 tradebot tradebot
   }
   ```

2. **Monitor Critical Events**
   ```bash
   # Watch for errors
   tail -f /var/log/tradebot/error.log
   
   # Watch trades
   grep "Executed" /var/log/tradebot/output.log | tail -20
   ```

### Alert Setup (Optional)

For production, consider:
- Email alerts on errors
- SMS alerts for critical failures
- Slack/Discord webhooks for trade notifications
- Monitoring tools (Prometheus, Grafana)

## Maintenance

### Daily Checks
- [ ] Verify bot is running: `systemctl status tradebot`
- [ ] Check error logs: `tail /var/log/tradebot/error.log`
- [ ] Review recent trades in database
- [ ] Verify account balance matches expectations

### Weekly Tasks
- [ ] Review performance metrics
- [ ] Check disk space: `df -h`
- [ ] Update dependencies: `poetry update`
- [ ] Review and adjust parameters if needed

### Monthly Tasks
- [ ] Full backup of database
- [ ] Security updates: `sudo apt update && sudo apt upgrade`
- [ ] Review strategy performance
- [ ] Audit trade history for anomalies

## Rollback Procedure

If issues occur:

1. **Stop the Bot**
   ```bash
   sudo systemctl stop tradebot
   ```

2. **Close Open Positions**
   - Manually close positions via Groww UI
   - Or use emergency script (if available)

3. **Restore Previous Version**
   ```bash
   cd TradeBot
   git checkout <previous-stable-tag>
   poetry install --no-root --no-dev
   ```

4. **Restore Database Backup**
   ```bash
   cp /home/tradebot/backups/autotrade_YYYYMMDD.db autotrade.db
   ```

5. **Restart After Verification**
   ```bash
   sudo systemctl start tradebot
   ```

## Troubleshooting

### Bot Won't Start
```bash
# Check service status
sudo systemctl status tradebot

# Check logs
sudo journalctl -u tradebot -n 50

# Verify configuration
cd ~/TradeBot && python main.py
```

### Authentication Errors
- Verify API token is valid and not expired
- Check network connectivity
- Ensure API rate limits not exceeded

### Database Locked
```bash
# Check for running processes
ps aux | grep python

# Kill if necessary
pkill -f "python main.py"

# Restart service
sudo systemctl restart tradebot
```

## Security Best Practices

1. **Never commit .env to git**
2. **Rotate API keys monthly**
3. **Use strong server passwords**
4. **Enable SSH key authentication**
5. **Monitor for unauthorized access**
6. **Keep system updated**
7. **Use firewall rules**
8. **Enable audit logging**

## Support

For deployment issues:
- Check [CODE_REVIEW_REPORT.md](CODE_REVIEW_REPORT.md)
- Open GitHub issue
- Contact: mo.kum4r@gmail.com

---

**Remember**: Trading with real money involves substantial risk. Start with small amounts and monitor closely!
