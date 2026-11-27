# Sequence diagram: UC-01 Register as respondent, with email confirmation (FR-01, FR-15)

```
Basis: team convention; diagrams/README.md (layers Presentation / Business / Data Source)
Source of truth: frontend/lib/features/auth/register_screen.dart, frontend/lib/features/auth/login_screen.dart,
  frontend/lib/features/auth/auth_repository.dart, backend/apps/api/views.py (RegisterView, TokenView),
  backend/apps/api/exceptions.py, backend/apps/users/views.py (confirm_email), backend/services/
  authentication_service.py (register_respondent, authenticate_user), backend/services/account_email_service.py
  (send_confirmation, confirm_email, EmailConfirmationTokenGenerator), backend/repositories/user_repository.py,
  backend/config/settings.py (EMAIL_BACKEND)
Date / version: 2026-11-27, develop commit 59f1957
```

A person registers in the app. The account is created unconfirmed and a confirmation link is emailed (printed in the
server window in development). Log-in is refused until the link is opened on the website. UC-07 (a provider registers
on the website) follows the same server steps from `apps/users/views.py`.

```mermaid
sequenceDiagram
    actor R as Respondent
    participant APP as RegisterScreen and LoginScreen (Flutter)
    participant V as RegisterView and TokenView (API views, Presentation)
    participant AU as AuthenticationService (service, Business)
    participant EM as AccountEmailService (service, Business)
    participant UR as User and Profile repositories (Data Source)
    participant DB as PostgreSQL
    participant MAIL as Email backend (console or SMTP)
    participant WEB as confirm_email (web view, Presentation)

    R->>APP: Fill in name, email, password, age, gender, governorate, interests
    APP->>V: POST /api/v1/auth/register/
    V->>AU: register_respondent(name, email, password, age, gender, region, interests)
    AU->>AU: normalise the email, reject a registered one, validate the password and profile
    AU->>UR: save user (RESPONDENT, ACTIVE, email_verified false) and profile, in one transaction
    UR->>DB: INSERT users, INSERT respondent_profiles
    AU-->>V: user
    V->>EM: send_confirmation(account, base address of the request)
    EM->>EM: link = /users/confirm-email/{uidb64}/{token}/ (salted token over id, email, email_verified)
    EM->>MAIL: send_mail("Confirm your Smart Survey email address", link)
    V-->>APP: 201 id, email, name, role (no tokens)
    APP-->>R: Log-in screen: Account created. We sent a confirmation link to the address. Open it, then log in.

    opt log-in before confirming
        R->>APP: Log in
        APP->>V: POST /api/v1/auth/token/
        V->>AU: authenticate_user(email, password)
        AU->>AU: password, then suspended or deleted, then email_verified
        AU-->>V: EmailNotConfirmed
        V-->>APP: 403 email_not_confirmed
        APP-->>R: Confirm your email address first. Open the link we sent you, or send a new one.
    end

    R->>WEB: Open the emailed link in a browser
    WEB->>EM: confirm_email(uidb64, token)
    EM->>UR: find_by_id(decoded id)
    alt token valid and not expired (3 days)
        EM->>UR: update(user with email_verified true)
        UR->>DB: UPDATE users SET email_verified true
        WEB-->>R: 302 to log-in with "Email confirmed. You can now log in."
    else used, expired or changed
        WEB-->>R: 302 to the resend page with "This link is not valid or has expired. Send a new one."
    end

    R->>APP: Log in
    APP->>V: POST /api/v1/auth/token/
    V->>AU: authenticate_user(email, password)
    AU-->>V: user
    V-->>APP: 200 access (30 minutes) and refresh (7 days)
    APP-->>R: Survey list (UC-03)
```

The confirmation token stops working once it is used, because `email_verified` is part of the signed value; no table
of codes exists. A wrong password gives 401 "Invalid email or password." before the confirmation is checked, so only
the account's owner learns that the address is unconfirmed. Accounts made by the team's commands and every account
that existed before migration 0017 are confirmed by default.

## Legend

| Symbol | Meaning |
|---|---|
| Stick figure | Actor: the person registering. |
| Box at the top | Lifeline: one object or group of objects; the label names it and its layer. |
| Solid arrow (`->>`) | Call, HTTP request or email sent. |
| Dashed arrow (`-->>`) | Return value or HTTP response with its status code. |
| Arrow back to the same lifeline | Internal step of that object. |
| `alt` / `else` frame | Alternatives: only one branch runs, chosen by the condition. |
| `opt` frame | Optional part: runs only when the person tries it. |
| `200`, `201`, `302`, `403` | HTTP status codes. |
