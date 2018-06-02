from sendgrid import Email, sendgrid
from sendgrid.helpers.mail import Content, Mail, Personalization


class Email_Client:
    """
    An email client for sending project applications to mentors and netsoc_mentorship applications to the admin email.
    Uses the sendgrid API.
    """

    _sg = None
    _sender_email = None
    _admin_email = None

    def __init__(self, sendgrid_key, sender_email, admin_email):
        """
        Initiated with the sendgrid API key, a list of recipients, and the admins email, as well as the sender email.
        :param sendgrid_key:
        :param sender_email:
        :param admin_email:
        """
        self._sg = sendgrid.SendGridAPIClient(apikey=sendgrid_key)
        self._sender_email = Email(sender_email)
        self._admin_email = Email(admin_email)

    def create_registration_completion_email(self, first_name, surname, link):
        subject = "NO-REPLY:ACM Wold Cup Predictor Competition Registration"
        message_body = """Hello {} {}\n
        Thank you for registering for our world cup predictor competition.
        You're nearly done. Just follow the link to complete registration\n\n
        Confirmation Link: {}\n\n
        We wish you the best of luck.""".format(first_name,
                                                surname,
                                                link)
        return subject, message_body

    def create_change_password_email(self, first_name, surname, link):
        subject = "NO-REPLY:ACM Wold Cup Predictor Competition Registration"
        message_body = """Hello {} {}\n
        You have requested to change your password. Please follow the link to do so.\n\n
        Change Password Link: {}\n\n
        We wish you the best of luck.""".format(first_name,
                                                surname,
                                                link)
        return subject, message_body

    def send_email(self, subject, message_body, recipients=[]):
        """
        Sends an email using the send grid API
        :param recipients:
        :param subject:
        :param message_body:
        :return:
        """
        content = Content("text/plain", message_body)
        mail = Mail(self._sender_email, subject, self._admin_email, content)

        if len(recipients) > 0:
            recipients_personalization = Personalization()
            for address in recipients:
                recipients_personalization.add_to(email=Email(address))
            mail.add_personalization(recipients_personalization)
        response = self._sg.client.mail.send.post(request_body=mail.get())
        return str(response.status_code).startswith("20")
