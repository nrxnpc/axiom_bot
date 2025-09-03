#!/bin/bash
# ==============================================================================
# Clipboard Workflow Script — Export project context as Markdown to clipboard
# ==============================================================================

set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
source "$SCRIPT_DIR/lib.sh"

pick_dir() {
    local prompt="${1:-Select a directory:}"
    notify prompt "$prompt" >&2
    gum file --directory --height 18
}

main() {
    notify accent "Clipboard Export" "Export all project or directory source files as Markdown. Sensitive files (like .env) are excluded."

    # --- Scope selection ---
    scope=$(choose "Select the context to export:" "Entire Project" "Specific Directory")
    if [[ "$scope" == "Entire Project" ]]; then
        selected_dir="$PROJECT_ROOT"
        scope_message="Entire project"
    else
        selected_dir=$(pick_dir "Select directory to export:") || { notify warn "Operation cancelled."; exit 0; }
        scope_message="$selected_dir"
    fi

    notify info "Context: $scope_message"

    # --- Collect files ---
    tmp_file=$(mktemp)
    tmp_list=$(mktemp)
    with_spinner "Scanning files..." \
        find "$selected_dir" -type f \
            -not -path "*/.git/*" \
            -not -path "*/.venv/*" \
            -not -path "*/__pycache__/*" \
            -not -name ".env" \
            -not -name "clipboard.md" \
            -not -name "*.pyc" \
            -not -name ".DS_Store" \
        | sort > "$tmp_list"

    files_list=()
    while read -r file; do
        if [[ $(file -b --mime-type "$file") == text/* || "$(basename "$file")" == "Makefile" ]]; then
            files_list+=("$file")
            {
                echo "---"
                echo ""
                echo "**File:** \`$file\`"
                echo ""
                ext="${file##*.}"
                lang=""
                case "$ext" in
                    sh) lang="bash";;
                    py) lang="python";;
                    md) lang="markdown";;
                    json) lang="json";;
                    yml|yaml) lang="yaml";;
                    env) lang="dotenv";;
                esac
                [[ "$(basename "$file")" = "Makefile" ]] && lang="makefile"
                echo "\`\`\`$lang"
                cat "$file"
                echo ""
                echo "\`\`\`"
                echo ""
            } >> "$tmp_file"
        fi
    done < "$tmp_list"

    if [ ! -s "$tmp_file" ]; then
        notify error "No text files found in the selected context."
        rm -f "$tmp_file" "$tmp_list"
        exit 1
    fi

    # --- Copy to clipboard ---
    copied="no"
    if command -v pbcopy > /dev/null; then
        cat "$tmp_file" | pbcopy
        copied="macOS clipboard"
    elif command -v xclip > /dev/null; then
        cat "$tmp_file" | xclip -selection clipboard
        copied="X11 clipboard"
    elif command -v wl-copy > /dev/null; then
        cat "$tmp_file" | wl-copy
        copied="Wayland clipboard"
    elif command -v clip.exe > /dev/null; then
        cat "$tmp_file" | clip.exe
        copied="Windows clipboard"
    else
        notify warn "Clipboard utility not found. Output saved to clipboard.md"
        cat "$tmp_file" > "$PROJECT_ROOT/clipboard.md"
        copied="clipboard.md file"
    fi
    notify success "Copied ${#files_list[@]} files to $copied."

    # --- List files included ---
    notify info "Files included:" "$(printf '\n- %s' "${files_list[@]}")"

    # --- Preview copied content ---
    if confirm "Preview copied context now?"; then
        preview_markdown "$tmp_file"
    fi

    rm -f "$tmp_file" "$tmp_list"
}

main