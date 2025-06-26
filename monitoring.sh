#!/bin/bash

PROJECT_DIR="$HOME/nsp_qr_bot"
LOG_FILE="$PROJECT_DIR/monitoring.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

check_services() {
    log "Проверка сервисов..."
    
    if systemctl is-active --quiet nsp-qr-bot; then
        log "✅ nsp-qr-bot: активен"
    else
        log "❌ nsp-qr-bot: неактивен"
    fi
    
    if systemctl is-active --quiet nsp-api-server; then
        log "✅ nsp-api-server: активен"
    else
        log "❌ nsp-api-server: неактивен"
    fi
    
    if systemctl is-active --quiet postgresql; then
        log "✅ postgresql: активен"
    else
        log "❌ postgresql: неактивен"
    fi
}

backup_database() {
    log "Создание backup базы данных..."
    BACKUP_DIR="$HOME/nsp_backups"
    mkdir -p "$BACKUP_DIR"
    
    DATE=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/nsp_qr_db_backup_$DATE.sql"
    
    if sudo -u postgres pg_dump nsp_qr_db > "$BACKUP_FILE"; then
        gzip "$BACKUP_FILE"
        log "✅ Backup создан: ${BACKUP_FILE}.gz"
        find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete
    else
        log "❌ Ошибка создания backup"
    fi
}

case "${1:-monitoring}" in
    "monitoring")
        check_services
        ;;
    "backup")
        backup_database
        ;;
    *)
        echo "Использование: $0 {monitoring|backup}"
        ;;
esac
