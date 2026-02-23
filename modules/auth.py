import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class AuthMiddleware:
    """Миделвара для проверки авторизации пользователей"""
    
    def __init__(self, allowed_user_ids):
        """
        Инициализация middleware
        
        Args:
            allowed_user_ids: список разрешенных ID пользователей
        """
        self.allowed_user_ids = allowed_user_ids
        logger.info(f"🔐 AuthMiddleware инициализирован. Разрешены ID: {allowed_user_ids}")
    
    async def check_auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Проверяет, авторизован ли пользователь
        
        Returns:
            True если пользователь авторизован, False если нет
        """
        if not update.effective_user:
            logger.warning("Попытка доступа без пользователя")
            return False
        
        user_id = update.effective_user.id
        username = update.effective_user.username or "без username"
        first_name = update.effective_user.first_name or ""
        
        # Проверяем, есть ли ID в белом списке
        if user_id in self.allowed_user_ids:
            logger.info(f"✅ Авторизован доступ: {first_name} @{username} (ID: {user_id})")
            return True
        else:
            logger.warning(f"❌ Заблокирован доступ: {first_name} @{username} (ID: {user_id})")
            return False
    
    async def handle_unauthorized(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Отправляет сообщение неавторизованному пользователю
        """
        message = (
            "❌ **Доступ запрещен**\n\n"
            "Этот бот предназначен для личного использования и доступен только его владельцу.\n\n"
            "Если вы хотите использовать этого бота, создайте свою копию на основе исходного кода."
        )
        
        # Пробуем отправить сообщение, но игнорируем ошибки
        try:
            await update.message.reply_text(message)
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения неавторизованному пользователю: {e}")
    
    async def handle_unauthorized_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обрабатывает нажатия на кнопки от неавторизованных пользователей
        """
        query = update.callback_query
        await query.answer()
        
        message = (
            "❌ Доступ запрещен\n\n"
            "Этот бот предназначен для личного использования."
        )
        
        try:
            await query.edit_message_text(message)
        except Exception as e:
            logger.error(f"Ошибка при ответе на callback неавторизованного пользователя: {e}")
