"""Invitation email body (spec AC-01, FR-12).

The raw token appears here and nowhere else outside the delivered message —
this module is the single point at which the token becomes visible to anyone
(spec BR-07, SC-06). Nothing in this file may be logged.
"""

from app.services.email.sender import EmailMessage

SUBJECT = "You have been invited to PFM"


def build_activation_url(template: str, raw_token: str) -> str:
    """Substitute the token into the configured template.

    `str.replace` rather than `str.format`, because an activation URL legitimately
    contains other braces or query syntax that `format` would try to interpret
    and fail on.
    """
    return template.replace("{token}", raw_token)


def build_invitation_email(
    *,
    to_email: str,
    raw_token: str,
    activation_url_template: str,
    expires_in_hours: int,
) -> EmailMessage:
    """Compose the activation email.

    The URL goes into both alternatives so a text-only client can still activate
    (test_cases TC-03).
    """
    url = build_activation_url(activation_url_template, raw_token)

    text_body = (
        "You have been invited to join PFM.\n\n"
        f"Activate your account within {expires_in_hours} hours:\n"
        f"{url}\n\n"
        "If the link has expired, ask the person who invited you to send a new one.\n"
        "If you were not expecting this invitation, you can ignore this message.\n"
    )

    html_body = (
        "<html><body>"
        "<h2>You have been invited to join PFM</h2>"
        f"<p>Activate your account within <strong>{expires_in_hours} hours</strong>:</p>"
        f'<p><a href="{url}">Activate my account</a></p>'
        f"<p>Or paste this link into your browser:<br>{url}</p>"
        "<hr>"
        "<p>If the link has expired, ask the person who invited you to send a new one. "
        "If you were not expecting this invitation, you can ignore this message.</p>"
        "</body></html>"
    )

    return EmailMessage(to=to_email, subject=SUBJECT, text_body=text_body, html_body=html_body)
