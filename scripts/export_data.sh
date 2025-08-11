#!/bin/bash
"""
BathyCat Data Transfer Script
============================

Exports BathyCat data to a Windows-compatible format for easy transfer.
Creates ZIP archives that can be easily copied to Windows.

Usage: ./scripts/export_data.sh [session_name] [destination]
"""

BATHYCAT_DATA="/media/usb-storage/bathycat"
EXPORT_DIR="/media/usb-storage/bathycat/exports"

# Create export directory if it doesn't exist
mkdir -p "$EXPORT_DIR"

# Function to export session data
export_session() {
    local session_name="$1"
    local dest_dir="$2"
    
    if [ -z "$session_name" ]; then
        echo "Available sessions:"
        ls -1 "$BATHYCAT_DATA/images/" 2>/dev/null || echo "No sessions found"
        return 1
    fi
    
    local session_path="$BATHYCAT_DATA/images/$session_name"
    
    if [ ! -d "$session_path" ]; then
        echo "Error: Session '$session_name' not found"
        return 1
    fi
    
    local export_file="$EXPORT_DIR/bathycat_${session_name}_$(date +%Y%m%d_%H%M%S).zip"
    
    echo "Exporting session: $session_name"
    echo "Creating: $export_file"
    
    # Create ZIP with images and metadata
    cd "$BATHYCAT_DATA"
    zip -r "$export_file" \
        "images/$session_name/" \
        "metadata/$session_name/" 2>/dev/null \
        "previews/$session_name/" 2>/dev/null
    
    echo "Export complete: $(du -h "$export_file" | cut -f1)"
    
    # If destination specified, copy there
    if [ -n "$dest_dir" ] && [ -d "$dest_dir" ]; then
        cp "$export_file" "$dest_dir/"
        echo "Copied to: $dest_dir/"
    fi
    
    echo ""
    echo "To transfer to Windows:"
    echo "1. Remove USB drive safely: sudo umount /media/usb-storage"
    echo "2. Connect to Windows PC"
    echo "3. Use Linux file recovery software to access ext4"
    echo "4. Or copy via network: scp $export_file user@windows-pc:/path/"
}

# Export all sessions
export_all() {
    local dest_dir="$1"
    
    echo "Exporting all sessions..."
    
    for session_dir in "$BATHYCAT_DATA/images"/*; do
        if [ -d "$session_dir" ]; then
            session_name=$(basename "$session_dir")
            export_session "$session_name" "$dest_dir"
        fi
    done
}

# Main script
case "${1:-help}" in
    "all")
        export_all "$2"
        ;;
    "list")
        echo "Available sessions:"
        ls -la "$BATHYCAT_DATA/images/" 2>/dev/null || echo "No sessions found"
        ;;
    "help"|"")
        echo "BathyCat Data Export Tool"
        echo "Usage:"
        echo "  $0 list              - List available sessions"
        echo "  $0 all [dest_dir]    - Export all sessions"  
        echo "  $0 [session] [dest]  - Export specific session"
        echo ""
        echo "Examples:"
        echo "  $0 list"
        echo "  $0 20250810_14"
        echo "  $0 all /tmp/exports"
        ;;
    *)
        export_session "$1" "$2"
        ;;
esac
