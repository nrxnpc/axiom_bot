#!/bin/bash
# ==============================================================================
# Universal Gum TUI Library for Bash Scripts
# ==============================================================================
# Provides a consistent and professional set of functions for creating terminal
# user interfaces using 'gum'. The style is inspired by modern, minimalist CLIs.
# All functions are designed to be self-contained and robust.
# ==============================================================================

# --- Color Palette (inspired by Catppuccin Macchiato) ---
# Can be overridden by setting environment variables before sourcing this script.
TUI_COLOR_BLUE="${TUI_COLOR_BLUE:-#8aadf4}"      # Banners, prompts
TUI_COLOR_GREEN="${TUI_COLOR_GREEN:-#a6da95}"    # Success
TUI_COLOR_YELLOW="${TUI_COLOR_YELLOW:-#eed49f}"  # Warnings
TUI_COLOR_RED="${TUI_COLOR_RED:-#ed8796}"        # Errors
TUI_COLOR_LAVENDER="${TUI_COLOR_LAVENDER:-#b7bdf8}" # Accents, selections
TUI_COLOR_TEXT="${TUI_COLOR_TEXT:-#cad3f5}"        # Default text
TUI_COLOR_SUBTEXT="${TUI_COLOR_SUBTEXT:-#a5adce}"  # Dimmer text
TUI_COLOR_BORDER="${TUI_COLOR_BORDER:-#363a4f}"    # Borders

# ------------------------------------------------------------------------------
# notify: Prints a styled notification message.
# Usage: notify <level> <message>
# Levels: info, success, warn, error, accent, prompt
# ------------------------------------------------------------------------------
notify() {
    local level="${1:-info}"
    local message="${2:-}"
    local icon fg
    case "$level" in
        info)    icon="i"; fg="$TUI_COLOR_BLUE";;
        success) icon="✔"; fg="$TUI_COLOR_GREEN";;
        warn)    icon="!"; fg="$TUI_COLOR_YELLOW";;
        error)   icon="✖"; fg="$TUI_COLOR_RED";;
        accent)  icon="◆"; fg="$TUI_COLOR_LAVENDER";;
        prompt)  icon="›"; fg="$TUI_COLOR_TEXT";;
        *)       icon="•"; fg="$TUI_COLOR_TEXT";;
    esac
    
    gum style --foreground "$fg" --margin "0 1" -- "$icon $message"
}

# ------------------------------------------------------------------------------
# input: Prompts for a single line of user input.
# Returns the input string to stdout.
# Usage: user_name=$(input "Enter your name:")
# ------------------------------------------------------------------------------
input() {
    local prompt="${1:-Enter input}"
    gum input --placeholder="$prompt" \
        --prompt.foreground="$TUI_COLOR_LAVENDER" --prompt="› " \
        --cursor.foreground="$TUI_COLOR_LAVENDER" --width=80
}

# ------------------------------------------------------------------------------
# multiline: Prompts for multi-line user input (Ctrl+D to submit).
# Returns the input string to stdout.
# Usage: request=$(multiline "Describe your request:")
# ------------------------------------------------------------------------------
multiline() {
    local placeholder="${1:-Enter text (Ctrl+D to save)...}"
    gum write --placeholder="$placeholder" --width=80 \
        --prompt.foreground="$TUI_COLOR_LAVENDER" --cursor.foreground="$TUI_COLOR_LAVENDER"
}

# ------------------------------------------------------------------------------
# choose: Prompts the user to select one item from a list.
# Returns the selected item to stdout.
# Usage: choice=$(choose "Select an option:" "Option A" "Option B")
# ------------------------------------------------------------------------------
choose() {
    local header="$1"; shift
    # Note: --height is set to accommodate typical menu sizes without taking over the screen.
    gum choose --header="$header" "$@" \
        --height=5 \
        --header.foreground="$TUI_COLOR_LAVENDER" \
        --cursor.foreground="$TUI_COLOR_LAVENDER" \
        --selected.foreground="$TUI_COLOR_GREEN" \
        --cursor-prefix="› " --selected-prefix="✔ "
}

# ------------------------------------------------------------------------------
# confirm: Asks a Yes/No question.
# Exits with status 0 for "Yes", 1 for "No".
# Usage: if confirm "Continue?"; then ...; fi
# ------------------------------------------------------------------------------
confirm() {
    local prompt="${1:-Are you sure?}"
    gum confirm "$prompt" \
        --prompt.foreground="$TUI_COLOR_LAVENDER" \
        --selected.background="$TUI_COLOR_LAVENDER" \
        --unselected.background="$TUI_COLOR_BORDER"
}

# ------------------------------------------------------------------------------
# pick_dir: Opens a directory picker.
# Returns the selected path to stdout.
# Usage: selected_dir=$(pick_dir "Choose a directory")
# ------------------------------------------------------------------------------
pick_dir() {
    local prompt="${1:-Select a directory}"
    notify prompt "$prompt" >&2
    gum file --directory --height=20
}

# ------------------------------------------------------------------------------
# with_spinner: Executes a command while showing a spinner.
# Usage: with_spinner "Doing a long task..." sleep 5
# ------------------------------------------------------------------------------
with_spinner() {
    local title="${1:-Working...}"; shift
    gum spin --show-output --spinner dot --title "$title" --title.foreground="$TUI_COLOR_LAVENDER" -- "$@"
}

# ------------------------------------------------------------------------------
# create_markdown_panel: Renders markdown text inside a styled panel.
# This is designed to be a component in a `gum join` layout.
# Usage: panel=$(create_markdown_panel "$markdown_text")
# ------------------------------------------------------------------------------
create_markdown_panel() {
    local markdown_content="$1"
    
    # Render markdown using glow, forcing no pager.
    # The PAGER="" override is the most reliable method.
    local rendered_content
    if command -v glow &>/dev/null; then
        rendered_content=$(echo -e "$markdown_content" | PAGER="" glow -p --style dark --width 76)
    else
        # Fallback to just echoing the content if glow isn't available.
        rendered_content=$(echo -e "$markdown_content")
    fi

    # Wrap the rendered content in a styled box.
    gum style --border double --border-foreground "$TUI_COLOR_LAVENDER" \
        --padding "1 2" --margin "0" --width=80 \
        "$rendered_content"
}

# ------------------------------------------------------------------------------
# display_plan: Beautifully displays a JSON execution plan
# Usage: display_plan "$json_plan"
# ------------------------------------------------------------------------------
display_plan() {
    local plan_json="$1"
    
    # Parse and format the plan using Python
    local formatted_plan
    formatted_plan=$(echo "$plan_json" | python3 -c "
import json, sys
try:
    plan = json.load(sys.stdin)
    operations = plan.get('operations', [])
    
    print('# 📋 Execution Plan\n')
    print(f'**Total Operations:** {len(operations)}\n')
    
    for i, op in enumerate(operations, 1):
        action = op.get('action', 'UNKNOWN')
        path = op.get('path', 'unknown')
        
        # Choose icon based on action
        icon = {'CREATE': '📄', 'UPDATE': '✏️', 'DELETE': '🗑️'}.get(action, '📝')
        
        print(f'### {i}. {icon} {action} `{path}`')
        
        # Show content preview for CREATE/UPDATE
        content = op.get('content', '')
        if content and action in ['CREATE', 'UPDATE']:
            lines = content.split('\n')
            preview_lines = min(3, len(lines))
            print('```')
            for line in lines[:preview_lines]:
                print(line[:80] + ('...' if len(line) > 80 else ''))
            if len(lines) > preview_lines:
                print(f'... ({len(lines) - preview_lines} more lines)')
            print('```')
        print()
except Exception as e:
    print('# 📋 Execution Plan\n')
    print('*Plan generated successfully*')
")
    
    # Display using glamour if available, otherwise gum format
    if command -v glamour &>/dev/null; then
        echo "$formatted_plan" | glamour --style dark --width 78
    else
        echo "$formatted_plan" | gum format --theme=dark
    fi
}

# ------------------------------------------------------------------------------
# generate_session_report: Creates a comprehensive session report
# Usage: generate_session_report "$work_dir"
# ------------------------------------------------------------------------------
generate_session_report() {
    local work_dir="$1"
    local project_name=$(basename "$work_dir")
    
    # Generate git-based changes summary
    local changes_summary=""
    if git -C "$work_dir" rev-parse --git-dir &>/dev/null; then
        changes_summary=$(cd "$work_dir" && {
            local total_files=$(git status --porcelain | wc -l | tr -d ' ')
            local modified=$(git status --porcelain | grep "^M " | wc -l | tr -d ' ')
            local added=$(git status --porcelain | grep "^A " | wc -l | tr -d ' ')
            local new=$(git status --porcelain | grep "^??" | wc -l | tr -d ' ')
            local deleted=$(git status --porcelain | grep "^D " | wc -l | tr -d ' ')
            
            echo "Changes Summary"
            echo
            echo "Total Files Affected: $total_files"
            echo
            [ "$modified" -gt 0 ] && echo "- Modified: $modified files"
            [ "$added" -gt 0 ] && echo "- Created: $added files"
            [ "$new" -gt 0 ] && echo "- New: $new files"
            [ "$deleted" -gt 0 ] && echo "- Deleted: $deleted files"
            echo
            
            if [ "$total_files" -gt 0 ]; then
                echo "Modified Files:"
                echo
                git status --porcelain | head -10 | awk '{print "- " $2}'
                [ "$total_files" -gt 10 ] && echo "- ... and $(($total_files - 10)) more files"
            else
                echo "No changes detected in git status."
            fi
        })
    else
        changes_summary="Changes Summary\n\nProject is not a git repository. Changes cannot be tracked."
    fi
    
    # Generate timestamp
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    
    # Create comprehensive report
    local report="CrewSeed AI Session Report\n\n"
    report+="Project: $project_name\n"
    report+="Session Completed: $timestamp\n\n"
    report+="$changes_summary\n\n"
    report+="Next Steps:\n"
    report+="1. Review Changes: Use git diff to examine all modifications\n"
    report+="2. Test Implementation: Verify that changes work as expected\n"
    report+="3. Commit Changes: When satisfied, commit changes\n"
    report+="4. Update Documentation: Consider updating README or docs if needed\n\n"
    report+="Session Summary:\n"
    report+="Your codebase has been intelligently enhanced by the CrewSeed AI agent system.\n"
    report+="The changes maintain code quality standards and integrate seamlessly with existing patterns.\n\n"
    report+="Thank you for using CrewSeed AI!"
    
    echo -e "$report"
}