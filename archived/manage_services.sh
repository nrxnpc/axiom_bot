#!/bin/bash

case "$1" in
    start)
        sudo systemctl start nsp-qr-bot nsp-api-server
        echo "Сервисы запущены"
        ;;
    stop)
        sudo systemctl stop nsp-qr-bot nsp-api-server
        echo "Сервисы остановлены"
        ;;
    restart)
        sudo systemctl restart nsp-qr-bot nsp-api-server
        echo "Сервисы перезапущены"
        ;;
    status)
        echo "=== Статус сервисов ==="
        sudo systemctl status nsp-qr-bot --no-pager -l
        echo ""
        sudo systemctl status nsp-api-server --no-pager -l
        ;;
    logs-bot)
        journalctl -u nsp-qr-bot -f
        ;;
    logs-api)
        journalctl -u nsp-api-server -f
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs-bot|logs-api}"
        ;;
esac
