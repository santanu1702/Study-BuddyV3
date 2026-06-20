# ============================================================
#         StudyBuddyV3BOT — Notes Handler
#         Save, view, delete personal study notes
#         Full inline button UI with pagination
# ============================================================

from telegram import Update
from telegram.ext import ContextTypes

from config.settings import settings
from config.constants import BotState, EmojiConstants, LimitConstants
from database.repositories import user_repo, notes_repo
from keyboards.notes_kb import NotesKeyboard
from utils.logger import get_logger
from utils.helpers import (
    edit_or_send,
    answer_callback,
    sanitize_input,
    format_datetime,
)

logger = get_logger(__name__)


# ============================================================
#   NOTES HANDLER
# ============================================================

class NotesHandler:
    """
    Handles all study notes interactions.

    Features:
    - Save notes with optional title
    - View notes with pagination (5 per page)
    - View individual note detail
    - Delete individual notes (with confirmation)
    - Delete all notes (with confirmation)
    - Search notes by keyword
    - Notes count tracking
    """

    # ================================================================
    #   CALLBACK ROUTER
    # ================================================================

    async def handle_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Route all notes: callback queries.
        Pattern: notes:action:param

        Actions:
        - open:       Open notes menu
        - save:       Start save note flow
        - list:       Show notes list (paginated)
        - view:       View single note detail
        - delete:     Delete single note (confirm)
        - delete_confirm: Confirm delete
        - delete_all: Delete all notes (confirm)
        - delete_all_confirm: Confirm delete all
        - search:     Start search flow
        - page:       Navigate to page number
        - back:       Back to notes menu
        - back_list:  Back to notes list
        """
        query   = update.callback_query
        user_id = update.effective_user.id
        await query.answer()

        parts  = query.data.split(":")
        action = parts[1] if len(parts) > 1 else ""
        param  = parts[2] if len(parts) > 2 else ""

        logger.debug(
            f"Notes callback | User: {user_id} | "
            f"Action: {action} | Param: {param}"
        )

        if action == "open":
            await self._show_notes_menu(update, context)
        elif action == "save":
            await self._prompt_save_note(update, context)
        elif action == "list":
            page = int(param) if param.isdigit() else 1
            await self._show_notes_list(update, context, page)
        elif action == "view":
            await self._view_note(update, context, param)
        elif action == "delete":
            await self._confirm_delete_note(update, context, param)
        elif action == "delete_confirm":
            await self._delete_note(update, context, param)
        elif action == "delete_all":
            await self._confirm_delete_all(update, context)
        elif action == "delete_all_confirm":
            await self._delete_all_notes(update, context)
        elif action == "page":
            page = int(param) if param.isdigit() else 1
            await self._show_notes_list(update, context, page)
        elif action == "back":
            await self._show_notes_menu(update, context)
        elif action == "back_list":
            await self._show_notes_list(update, context, 1)
        elif action == "cancel":
            context.user_data["state"] = BotState.IDLE
            context.user_data.pop("note_title", None)
            await self._show_notes_menu(update, context)
        else:
            await self._show_notes_menu(update, context)

    # ================================================================
    #   NOTES MENU
    # ================================================================

    async def _show_notes_menu(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Display the main notes menu with stats."""
        user_id = update.effective_user.id

        # Get notes count
        count    = await notes_repo.count_user_notes(user_id)
        capacity = LimitConstants.MAX_NOTES_PER_USER
        recent   = await notes_repo.get_recent_notes(user_id, limit=3)

        # Build recent notes preview
        recent_text = ""
        if recent:
            recent_text = "\n📌 *Recent Notes:*\n"
            for note in recent:
                title   = note.display_title[:30]
                created = format_datetime(note.created_at)
                recent_text += f"  • _{title}_ — {created}\n"
        else:
            recent_text = "\n_No notes saved yet._"

        text = (
            f"{EmojiConstants.NOTES} *Study Notes*\n"
            f"{'─' * 35}\n\n"
            f"📊 Notes: `{count}` / `{capacity}`\n"
            f"{recent_text}\n\n"
            f"_What would you like to do?_"
        )

        keyboard = NotesKeyboard.notes_menu(has_notes=count > 0)
        await edit_or_send(update, context, text, keyboard)

    # ================================================================
    #   SAVE NOTE
    # ================================================================

    async def _prompt_save_note(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Start the save note flow.
        Check capacity first, then prompt for content.
        """
        user_id = update.effective_user.id

        # Check capacity
        has_capacity = await notes_repo.user_has_capacity(user_id)
        if not has_capacity:
            count = await notes_repo.count_user_notes(user_id)
            text  = (
                f"{EmojiConstants.WARNING} *Notes Limit Reached*\n\n"
                f"You have `{count}` / "
                f"`{LimitConstants.MAX_NOTES_PER_USER}` notes.\n\n"
                f"Please delete some notes before saving new ones."
            )
            keyboard = NotesKeyboard.back_to_menu()
            await edit_or_send(update, context, text, keyboard)
            return

        # Set state
        context.user_data["state"]      = BotState.AWAITING_NOTE_CONTENT
        context.user_data["note_title"] = ""

        text = (
            f"{EmojiConstants.SAVE} *Save New Note*\n"
            f"{'─' * 35}\n\n"
            f"📝 Send your note content now.\n\n"
            f"You can include:\n"
            f"  • Plain text\n"
            f"  • Formulas or equations\n"
            f"  • Lists or bullet points\n"
            f"  • Any study material\n\n"
            f"📏 Max length: "
            f"`{LimitConstants.MAX_NOTE_CONTENT_LENGTH}` characters\n\n"
            f"_Tip: Start with a title on the first line!_"
        )

        keyboard = NotesKeyboard.cancel_button()
        await edit_or_send(update, context, text, keyboard)

    async def handle_note_input(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Process note content input from user.
        Called from main.py router when state = AWAITING_NOTE_CONTENT.

        Auto-extracts title from first line if present.
        """
        user_id  = update.effective_user.id
        text_in  = update.message.text.strip()

        # Reset state
        context.user_data["state"] = BotState.IDLE

        # Validate input
        if not text_in:
            await update.message.reply_text(
                f"{EmojiConstants.ERROR} Note content cannot be empty."
            )
            return

        if len(text_in) > LimitConstants.MAX_NOTE_CONTENT_LENGTH:
            await update.message.reply_text(
                f"{EmojiConstants.WARNING} Note is too long.\n"
                f"Max `{LimitConstants.MAX_NOTE_CONTENT_LENGTH}` characters.\n"
                f"Your note: `{len(text_in)}` characters.",
                parse_mode="Markdown",
            )
            return

        # Sanitize
        text_in = sanitize_input(text_in)

        # Auto-extract title from first line
        lines   = text_in.split("\n")
        title   = ""
        content = text_in

        if len(lines) > 1 and len(lines[0]) <= LimitConstants.MAX_NOTE_TITLE_LENGTH:
            title   = lines[0].strip()
            content = "\n".join(lines[1:]).strip()
            if not content:
                # Only one line — use as content, no title
                title   = ""
                content = text_in
        elif len(lines) == 1:
            # Single line — use as content
            content = text_in

        # Check capacity again (race condition protection)
        has_capacity = await notes_repo.user_has_capacity(user_id)
        if not has_capacity:
            await update.message.reply_text(
                f"{EmojiConstants.WARNING} Notes limit reached. "
                f"Please delete some notes first."
            )
            return

        # Save note
        note = await notes_repo.create(
            user_id= user_id,
            content= content,
            title=   title,
        )

        if note:
            # Update user's notes count
            await user_repo.update_notes_count(user_id, delta=1)

            # Get new total count
            count = await notes_repo.count_user_notes(user_id)

            await update.message.reply_text(
                f"{EmojiConstants.SUCCESS} *Note Saved!*\n\n"
                f"📝 Title: _{note.display_title}_\n"
                f"📏 Length: `{len(content)}` characters\n"
                f"📊 Total Notes: `{count}` / "
                f"`{LimitConstants.MAX_NOTES_PER_USER}`\n\n"
                f"_Use the Notes menu to view or manage your notes._",
                parse_mode="Markdown",
                reply_markup=NotesKeyboard.after_save(),
            )

            logger.info(
                f"📚 Note saved | "
                f"User: {user_id} | "
                f"ID: {note.note_id[:8]} | "
                f"Title: {note.display_title!r}"
            )
        else:
            await update.message.reply_text(
                f"{EmojiConstants.ERROR} Failed to save note. "
                f"Please try again."
            )

    # ================================================================
    #   VIEW NOTES LIST
    # ================================================================

    async def _show_notes_list(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        page:    int = 1,
    ) -> None:
        """
        Display paginated list of user's notes.
        Shows 5 notes per page with navigation buttons.
        """
        user_id = update.effective_user.id

        # Get paginated notes
        page_data = await notes_repo.get_notes_page(
            user_id=  user_id,
            page=     page,
            per_page= LimitConstants.NOTES_PER_PAGE,
        )

        notes       = page_data["notes"]
        total       = page_data["total"]
        total_pages = page_data["total_pages"]
        has_next    = page_data["has_next"]
        has_prev    = page_data["has_prev"]

        if not notes:
            text = (
                f"{EmojiConstants.NOTES} *My Notes*\n"
                f"{'─' * 35}\n\n"
                f"📭 You have no saved notes yet.\n\n"
                f"_Tap 'Save Note' to create your first note!_"
            )
            keyboard = NotesKeyboard.empty_notes()
            await edit_or_send(update, context, text, keyboard)
            return

        # Build notes list
        notes_text = ""
        start_idx  = (page - 1) * LimitConstants.NOTES_PER_PAGE + 1

        for i, note in enumerate(notes, start_idx):
            title   = note.display_title[:35]
            preview = note.short_content[:50]
            created = format_datetime(note.created_at)
            notes_text += (
                f"*{i}.* _{title}_\n"
                f"   {preview}\n"
                f"   🕐 _{created}_\n\n"
            )

        text = (
            f"{EmojiConstants.NOTES} *My Notes* "
            f"({total} total)\n"
            f"{'─' * 35}\n\n"
            f"{notes_text}"
            f"_Page {page} of {total_pages}_"
        )

        keyboard = NotesKeyboard.notes_list(
            notes=       notes,
            page=        page,
            total_pages= total_pages,
            has_next=    has_next,
            has_prev=    has_prev,
        )

        await edit_or_send(update, context, text, keyboard)

    # ================================================================
    #   VIEW SINGLE NOTE
    # ================================================================

    async def _view_note(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        note_id: str,
    ) -> None:
        """Display full content of a single note."""
        user_id = update.effective_user.id

        if not note_id:
            await self._show_notes_menu(update, context)
            return

        note = await notes_repo.get_by_id(
            note_id= note_id,
            user_id= user_id,
        )

        if not note:
            await answer_callback(
                update.callback_query,
                text="⚠️ Note not found or already deleted.",
                show_alert=True,
            )
            await self._show_notes_list(update, context, 1)
            return

        created = format_datetime(note.created_at)
        updated = format_datetime(note.updated_at)

        # Truncate content if too long for message
        content = note.content
        if len(content) > 3000:
            content = content[:2997] + "..."

        text = (
            f"{EmojiConstants.NOTES} *{note.display_title}*\n"
            f"{'─' * 35}\n\n"
            f"{content}\n\n"
            f"{'─' * 35}\n"
            f"🕐 Created: _{created}_\n"
            f"✏️ Updated: _{updated}_\n"
            f"🆔 ID: `{note.note_id[:8]}`"
        )

        keyboard = NotesKeyboard.note_detail(note_id=note.note_id)
        await edit_or_send(update, context, text, keyboard)

    # ================================================================
    #   DELETE NOTE
    # ================================================================

    async def _confirm_delete_note(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        note_id: str,
    ) -> None:
        """Show confirmation dialog before deleting a note."""
        user_id = update.effective_user.id

        note = await notes_repo.get_by_id(
            note_id= note_id,
            user_id= user_id,
        )

        if not note:
            await answer_callback(
                update.callback_query,
                text="⚠️ Note not found.",
                show_alert=True,
            )
            return

        text = (
            f"{EmojiConstants.DELETE} *Delete Note?*\n"
            f"{'─' * 35}\n\n"
            f"📝 *{note.display_title}*\n\n"
            f"_{note.short_content}_\n\n"
            f"⚠️ This action cannot be undone."
        )

        keyboard = NotesKeyboard.delete_confirm(note_id=note_id)
        await edit_or_send(update, context, text, keyboard)

    async def _delete_note(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        note_id: str,
    ) -> None:
        """
        Soft-delete a note after confirmation.
        Updates user's notes count in DB.
        """
        user_id = update.effective_user.id

        success = await notes_repo.delete(
            note_id= note_id,
            user_id= user_id,
        )

        if success:
            # Decrement user's notes count
            await user_repo.update_notes_count(user_id, delta=-1)

            await answer_callback(
                update.callback_query,
                text="🗑️ Note deleted successfully.",
                show_alert=False,
            )

            # Return to notes list
            await self._show_notes_list(update, context, 1)

            logger.info(
                f"🗑️ Note deleted | "
                f"User: {user_id} | "
                f"ID: {note_id[:8]}"
            )
        else:
            await answer_callback(
                update.callback_query,
                text="❌ Failed to delete note.",
                show_alert=True,
            )

    async def _confirm_delete_all(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Show confirmation dialog before deleting ALL notes."""
        user_id = update.effective_user.id
        count   = await notes_repo.count_user_notes(user_id)

        text = (
            f"{EmojiConstants.DELETE} *Delete ALL Notes?*\n"
            f"{'─' * 35}\n\n"
            f"⚠️ You are about to delete *{count} notes*.\n\n"
            f"This will permanently remove all your saved notes.\n"
            f"*This action cannot be undone!*"
        )

        keyboard = NotesKeyboard.delete_all_confirm()
        await edit_or_send(update, context, text, keyboard)

    async def _delete_all_notes(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """
        Delete all notes for a user after confirmation.
        Resets user's notes count to 0.
        """
        user_id = update.effective_user.id

        deleted_count = await notes_repo.delete_all_user_notes(user_id)

        if deleted_count > 0:
            # Reset notes count in user document
            await user_repo.update(
                user_id= user_id,
                updates= {"notes_count": 0},
            )

            text = (
                f"{EmojiConstants.SUCCESS} *All Notes Deleted*\n\n"
                f"🗑️ Deleted `{deleted_count}` notes successfully.\n\n"
                f"_Your notes collection is now empty._"
            )

            logger.info(
                f"🗑️ All notes deleted | "
                f"User: {user_id} | "
                f"Count: {deleted_count}"
            )
        else:
            text = (
                f"{EmojiConstants.INFO} *No Notes Found*\n\n"
                f"_You have no notes to delete._"
            )

        keyboard = NotesKeyboard.back_to_menu()
        await edit_or_send(update, context, text, keyboard)