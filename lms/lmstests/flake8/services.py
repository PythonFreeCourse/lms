import logging
import tempfile
import typing

from flake8.main import application

from lms.lmsdb import models


class PyFlakeResponse(typing.NamedTuple):
    error_code: str
    line_number: int
    column: int
    text: str
    physical_line: str


FLAKE_ERRORS_MAPPING = {
    'Q000': 'השתמש בצוקואים בודדים ולא בגרשיים',
    "E902": "כשהבודק שלנו ניסה להריץ את הקוד שלך, הוא ראה שלפייתון הייתה בעיה בלהבין אותו. יש מצב ששכחת לסגור מקף, גרשיים או סוגריים? זה לא חייב להיות דווקא בשורה הזו, אז כדאי להסתכל קצת למעלה.",
    "F401": "יבאת מודול ולא עשית בו שימוש במהלך הקוד.",
    "E741": "חשוב לנו ששמות המשתנים שלך יהיו טובים. כדאי לבחור שם משתנה בעל משמעות, באותיות קטנות, שמתאר היטב את תוכן המשתנה. אם יש כמה מילים בשם המשתנה, ניתן להשתמש בקו תחתון (_) כדי להפריד אותן אחת מהשנייה.",
    "E225": "חסר לך רווחים מסביב לאופרטור בשורה הזו.",
    "E226": "חסר לך רווחים מסביב לאופרטור החשבוני בשורה הזו.",
    "E231": "המלצה: נחשב משמעותית יותר יפה לשים רווח אחרי פסיק, ממש כמו בעברית.",
    "F821": "שם המשתנה שמופיע פה לא הוגדר. אם הוא כן הוגדר בתאים אחרים במחברת, הוסיפו אותו לתא כדי שהבודק יוכל להתייחס לפתרון שלכם.",
    "E261": "בשורות קוד בהן מופיעה גם הערה, מקובל לשים לפחות שני רווחים לפני התו סולמית כדי לבדל את הקוד מההערה.",
    "E211": "כדי לשמור על הקוד מסודר ויפה, מומלץ שלא לשים רווחים לפני תו של פתיחת סוגריים.",
    "W291": "מצאנו שהתגנבו לך רווחים אחרי התו האחרון בשורה. לפתרון מושלם, נקו את הרווחים הללו.",
    "E262": "הערות צריכות להתחיל בתווים סולמית ואז רווח מיד אחרי.",
    "E228": "חסרים לך רווחים מסביב לאופרטור של המודולו.",
    "W293": "השורה הריקה פה מכילה רווחים. לפתרון מושלם, עדיף להוריד אותם.",
    "E202": "כדי לשמור על הקוד מסודר ויפה, מומלץ שלא לשים רווחים לפני תו של סגירת סוגריים.",
    "E265": "הערות צריכות להתחיל בתווים סולמית ואז רווח מיד אחרי.",
    "E712": "הנה אתגר מעניין: האם אפשר לבדוק שערך שווה ל־True בצורה קצרה יותר?",
    "E302": "אנחנו ממליצים פה על 2 ירידות שורה כדי להפריד בין חלקי הקוד.",
    "E305": "אנחנו ממליצים להפריד בין פונקציות או מחלקות בעזרת 2 ירידות שורה.",
    "E113": "יש לנו פה בעיה עם ההזחה של הקוד. יש מצב ששורות מסוימות התחילו ברווחים איפה שלא צריך?",
    "E999": "כשהבודק שלנו ניסה להריץ את הקוד שלך, הוא ראה שלפייתון יש בעיה להבין אותו. כדאי לוודא שהקוד רץ כהלכה לפני שמגישים אותו.",
    "E201": "כדי לשמור על הקוד מסודר ויפה, מומלץ שלא לשים רווחים אחרי תו של סגירת סוגריים.",
    "E271": "מצאנו יותר מרווח אחד אחרי מילת המפתח בשורה הזו. זה אמנם יעבוד, אבל זה נחשב לא כזה מנומס. תוכלו לתקן בבקשה?",
    "E221": "מצאנו יותר מרווח אחד לפני אופרטור בשורה הזו. זה אמנם יעבוד, אבל זה נחשב לא כזה מנומס. תוכלו לתקן בבקשה?",
    "E222": "מצאנו יותר מרווח אחד אחרי אופרטור בשורה הזו. זה אמנם יעבוד, אבל זה נחשב לא כזה מנומס. תוכלו לתקן בבקשה?",
    "E203": "מצאנו רווח לפני נקודתיים בשורה הזו. כדי לשמור על הקוד נקי, עדיף להסיר אותן.",
    "E272": "מצאנו יותר מרווח אחד לפני מילת המפתח בשורה הזו. זה אמנם יעבוד, אבל זה נחשב לא כזה מנומס. תוכלו לתקן בבקשה?",
    "E111": "הזחה (הזזה של שורה שמאלה בעזרת רווחים או טאבים) בקוד פייתון נאה חייבת להיות מורכבת מכפולות של 4 רווחים.",
    "E703": "בפייתון אנחנו לא משתמשים בנקודה פסיק כדי לסיים שורות קוד או ביטויים.",
    "E713": "כשאנחנו רוצים למצוא האם משהו לא נמצא בתוך משהו אחר, אנחנו נעדיף להשתמש ב־'not in'.",
    "W503": "עדיף לשים את האופרטור הלוגי אחרי שבירת השורה.",
    "E227": "חסרים רווחים מסביב לאופרטורים הבינאריים בשורה הזו.",
    "C819": "הפסיק פה לא הכרחי.",
    "E114": "הזחה (הזזה של שורה שמאלה בעזרת רווחים או טאבים) בקוד פייתון נאה חייבת להיות מורכבת מכפולות של 4 רווחים.",
    "E116": "משהו לא כל־כך עובד בהזחה פה. בדקו אותה שוב.",
    "E303": "הושארו פה יותר מדי שורות ריקות, צמצמו אותן קצת :)"
}

FLAKE_SKIP_ERRORS = (
    'T001',  # print found
    'W292',  # no new line in the end of the code
    'S322',  # input is a dangerous method of Python 2 yada yada
    'E501',  # > 79
    'W391',  # blank lines at the end of file
    'A001',  # known builtin method override
    'E128',  # continuation line under-indented for visual indent
    'S311',  # pseudo-random generators warning
    'Q001',  # bad quotes
    'Q002',  # bad quotes on docstring
    'T002',  # Python 2.x reserved word print used
    'Q003',  # Change outer quotes for internal escaping
    'E127',  # continuation line over-indented for visual indent
)


class PyFlakeChecker:
    def __init__(self, solution_check_pk: str, logger: logging.Logger):
        self.solution_id = solution_check_pk
        self._app = None
        self._solution = None
        self._logger = logger

    def initialize(self):
        self._app = application.Application()
        self._app.initialize(argv=[])
        self._solution = models.Solution.get_by_id(self.solution_id)

    @property
    def app(self) -> application.Application:
        return self._app

    @property
    def solution(self) -> models.Solution:
        return self._solution

    def run_check(self):
        self._logger.info('checks errors on solution %s', self.solution_id)
        errors = self._get_errors_from_solution()

        for error in errors:
            if error.error_code in FLAKE_SKIP_ERRORS:
                self._logger.info(
                    'Skipping error %s to solution %s',
                    error, self.solution_id)
                continue

            self._logger.info('Adding error %s to solution %s',
                              error, self.solution_id)
            text = FLAKE_ERRORS_MAPPING.get(
                error.error_code, f'{error.error_code}-{error.text}')
            comment = models.CommentText.create_comment(
                text=text,
                flake_key=error.error_code,
            )
            models.Comment.create(
                commenter=models.User.get_system_user(),
                line_number=error.line_number,
                comment=comment,
                solution=self.solution,
            )

    def _get_errors_from_solution(self) -> typing.List[PyFlakeResponse]:
        errors = []
        code_content = self.solution.code
        index_of_check = 0
        with tempfile.NamedTemporaryFile('w') as temp_file:
            temp_file.write(code_content)
            temp_file.flush()

            self.app.run_checks([temp_file.name])
            results = self.app.file_checker_manager.checkers[
                index_of_check].results
            for result in results:
                errors.append(PyFlakeResponse(*result))
        return errors
