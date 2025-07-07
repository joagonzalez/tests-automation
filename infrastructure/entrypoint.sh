#!/bin/bash

# Entrypoint script for Benchmark Analyzer API
# =============================================

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Wait for service to be ready
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local timeout=${4:-60}

    log_info "Waiting for $service_name at $host:$port..."

    local count=0
    while ! nc -z "$host" "$port"; do
        if [ $count -ge $timeout ]; then
            log_error "Timeout waiting for $service_name"
            exit 1
        fi

        count=$((count + 1))
        log_info "Waiting for $service_name... ($count/$timeout)"
        sleep 1
    done

    log_success "$service_name is ready!"
}

# Wait for MySQL to be ready
wait_for_mysql() {
    local host=${DB_HOST:-localhost}
    local port=${DB_PORT:-3306}
    local user=${DB_USER:-root}
    local password=${DB_PASSWORD:-}
    local database=${DB_NAME:-perf_framework}

    log_info "Checking MySQL connection..."

    # First wait for port to be open
    wait_for_service "$host" "$port" "MySQL"

    # Then try to connect to MySQL
    local count=0
    local max_attempts=30

    while [ $count -lt $max_attempts ]; do
        if python -c "
import pymysql
try:
    conn = pymysql.connect(host='$host', port=$port, user='$user', password='$password', database='$database')
    conn.close()
    exit(0)
except Exception:
    exit(1)
" 2>/dev/null; then
            log_success "MySQL database connection successful!"
            return 0
        fi

        count=$((count + 1))
        log_info "Attempting MySQL connection... ($count/$max_attempts)"
        sleep 2
    done

    log_error "Failed to connect to MySQL after $max_attempts attempts"
    exit 1
}

# Initialize database
init_database() {
    log_info "Initializing database..."

    # Use Python to initialize the database
    python -c "
import sys
sys.path.insert(0, '/app')
from benchmark_analyzer.db.connector import get_db_manager
from benchmark_analyzer.config import get_config

try:
    config = get_config()
    db_manager = get_db_manager(config)
    db_manager.initialize_tables()
    print('Database initialized successfully')
except Exception as e:
    print(f'Database initialization failed: {e}')
    sys.exit(1)
"

    if [ $? -eq 0 ]; then
        log_success "Database initialization completed"
    else
        log_error "Database initialization failed"
        exit 1
    fi
}

# Check health of dependencies
health_check() {
    log_info "Performing health checks..."

    # Check if we can import required modules
    python -c "
import sys
sys.path.insert(0, '/app')

try:
    from benchmark_analyzer.config import get_config
    from benchmark_analyzer.db.connector import get_db_manager
    from api.main import create_app
    print('All modules imported successfully')
except Exception as e:
    print(f'Module import failed: {e}')
    sys.exit(1)
"

    if [ $? -eq 0 ]; then
        log_success "Health checks passed"
    else
        log_error "Health checks failed"
        exit 1
    fi
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."

    local dirs=(
        "/app/uploads"
        "/app/temp"
        "/app/logs"
    )

    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "Created directory: $dir"
        fi
    done

    log_success "Directories created"
}

# Set up environment
setup_environment() {
    log_info "Setting up environment..."

    # Set default values if not provided
    export DB_HOST=${DB_HOST:-mysql}
    export DB_PORT=${DB_PORT:-3306}
    export DB_USER=${DB_USER:-benchmark}
    export DB_PASSWORD=${DB_PASSWORD:-benchmark123}
    export DB_NAME=${DB_NAME:-perf_framework}
    export API_HOST=${API_HOST:-0.0.0.0}
    export API_PORT=${API_PORT:-8000}
    export ENVIRONMENT=${ENVIRONMENT:-development}
    export LOG_LEVEL=${LOG_LEVEL:-INFO}

    log_info "Environment: $ENVIRONMENT"
    log_info "API Host: $API_HOST"
    log_info "API Port: $API_PORT"
    log_info "Database Host: $DB_HOST"
    log_info "Database Port: $DB_PORT"
    log_info "Database Name: $DB_NAME"
    log_info "Log Level: $LOG_LEVEL"

    log_success "Environment setup completed"
}

# Main execution
main() {
    log_info "Starting Benchmark Analyzer API..."
    log_info "Container started at $(date)"

    # Setup environment
    setup_environment

    # Create directories
    create_directories

    # Wait for dependencies
    if [ "${SKIP_WAIT:-false}" != "true" ]; then
        wait_for_mysql
    else
        log_warning "Skipping dependency wait (SKIP_WAIT=true)"
    fi

    # Health checks
    health_check

    # Initialize database
    if [ "${SKIP_DB_INIT:-false}" != "true" ]; then
        init_database
    else
        log_warning "Skipping database initialization (SKIP_DB_INIT=true)"
    fi

    log_success "Startup sequence completed successfully"
    log_info "Starting API server..."

    # Execute the main command
    exec "$@"
}

# Handle signals
trap 'log_info "Received SIGTERM, shutting down gracefully..."; exit 0' SIGTERM
trap 'log_info "Received SIGINT, shutting down gracefully..."; exit 0' SIGINT

# Check if running in debug mode
if [ "${DEBUG:-false}" = "true" ]; then
    log_warning "Debug mode enabled"
    set -x
fi

# Run main function
main "$@"
