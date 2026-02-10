"""h4ckath0n quickstart – passkey-first auth with protected endpoints.

Run:
    uv run uvicorn examples.quickstart:app --reload

Open http://localhost:8000/docs to interact with the API.

Auth flow (passkeys):
    1. POST /auth/passkey/register/start  → get options
    2. (browser) navigator.credentials.create(options)
    3. POST /auth/passkey/register/finish → get tokens
    4. Use access_token in Authorization header

See /passkey-demo for a minimal browser-based example.
"""

from h4ckath0n import create_app
from h4ckath0n.auth import require_admin, require_scopes, require_user

app = create_app()


@app.get("/me")
def me(user=require_user()):
    """Return current user info (requires passkey login)."""
    return {"id": user.id, "role": user.role}


@app.get("/admin/dashboard")
def admin_dashboard(user=require_admin()):
    """Admin-only endpoint."""
    return {"ok": True, "admin_id": user.id}


@app.post("/billing/refund")
def refund(claims=require_scopes("billing:refund")):
    """Scoped endpoint – requires billing:refund scope in JWT."""
    return {"status": "queued"}


@app.get("/llm-demo")
def llm_demo():
    """LLM wrapper demo (requires OPENAI_API_KEY)."""
    try:
        from h4ckath0n.llm import llm

        client = llm()
        resp = client.chat(
            system="You are a helpful assistant.",
            user="Say hello in one sentence.",
        )
        return {"text": resp.text}
    except RuntimeError as exc:
        return {"error": str(exc)}


PASSKEY_DEMO_HTML = """<!DOCTYPE html>
<html><head><title>h4ckath0n Passkey Demo</title></head>
<body>
<h1>h4ckath0n Passkey Demo</h1>
<button id="register">Register (create account)</button>
<button id="login">Login</button>
<button id="add" disabled>Add another passkey</button>
<pre id="output"></pre>
<script>
const API = '';
let token = null;

function b64url(buf) {
    return btoa(String.fromCharCode(...new Uint8Array(buf)))
        .replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,'');
}
function b64urlDecode(s) {
    s = s.replace(/-/g,'+').replace(/_/g,'/');
    while(s.length%4) s+='=';
    return Uint8Array.from(atob(s), c=>c.charCodeAt(0));
}
function log(msg) { document.getElementById('output').textContent += msg + '\\n'; }

async function register() {
    log('Starting registration...');
    const start = await fetch(API+'/auth/passkey/register/start', {method:'POST'});
    const {flow_id, options} = await start.json();
    options.challenge = b64urlDecode(options.challenge);
    options.user.id = b64urlDecode(options.user.id);
    if(options.excludeCredentials) options.excludeCredentials.forEach(c=>c.id=b64urlDecode(c.id));
    const cred = await navigator.credentials.create({publicKey: options});
    const body = {
        flow_id,
        credential: {
            id: cred.id, rawId: b64url(cred.rawId), type: cred.type,
            response: {
                attestationObject: b64url(cred.response.attestationObject),
                clientDataJSON: b64url(cred.response.clientDataJSON),
            }
        }
    };
    const finish = await fetch(API+'/auth/passkey/register/finish', {
        method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)
    });
    const result = await finish.json();
    if(result.access_token) {
        token = result.access_token;
        document.getElementById('add').disabled=false;
    }
    log('Register result: ' + JSON.stringify(result, null, 2));
}

async function login() {
    log('Starting login...');
    const start = await fetch(API+'/auth/passkey/login/start', {method:'POST'});
    const {flow_id, options} = await start.json();
    options.challenge = b64urlDecode(options.challenge);
    if(options.allowCredentials) {
        options.allowCredentials.forEach(c=>c.id=b64urlDecode(c.id));
    }
    const cred = await navigator.credentials.get({publicKey: options});
    const body = {
        flow_id,
        credential: {
            id: cred.id, rawId: b64url(cred.rawId), type: cred.type,
            response: {
                authenticatorData: b64url(cred.response.authenticatorData),
                clientDataJSON: b64url(cred.response.clientDataJSON),
                signature: b64url(cred.response.signature),
                userHandle: cred.response.userHandle
                    ? b64url(cred.response.userHandle) : null,
            }
        }
    };
    const finish = await fetch(API+'/auth/passkey/login/finish', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify(body)
    });
    const result = await finish.json();
    if(result.access_token) {
        token = result.access_token;
        document.getElementById('add').disabled=false;
    }
    log('Login result: ' + JSON.stringify(result, null, 2));
}

async function addPasskey() {
    if(!token) { log('Login first'); return; }
    log('Adding passkey...');
    const start = await fetch(API+'/auth/passkey/add/start', {
        method:'POST', headers:{'Authorization':'Bearer '+token}
    });
    const {flow_id, options} = await start.json();
    options.challenge = b64urlDecode(options.challenge);
    options.user.id = b64urlDecode(options.user.id);
    if(options.excludeCredentials) {
        options.excludeCredentials.forEach(c=>c.id=b64urlDecode(c.id));
    }
    const cred = await navigator.credentials.create({publicKey: options});
    const body = {
        flow_id,
        credential: {
            id: cred.id, rawId: b64url(cred.rawId), type: cred.type,
            response: {
                attestationObject: b64url(cred.response.attestationObject),
                clientDataJSON: b64url(cred.response.clientDataJSON),
            }
        }
    };
    const finish = await fetch(API+'/auth/passkey/add/finish', {
        method:'POST',
        headers:{
            'Content-Type':'application/json',
            'Authorization':'Bearer '+token
        },
        body:JSON.stringify(body)
    });
    log('Add result: ' + JSON.stringify(await finish.json(), null, 2));
}

document.getElementById('register').onclick = register;
document.getElementById('login').onclick = login;
document.getElementById('add').onclick = addPasskey;
</script>
</body></html>"""


from fastapi.responses import HTMLResponse  # noqa: E402


@app.get("/passkey-demo", response_class=HTMLResponse)
def passkey_demo():
    """Minimal browser UI for testing passkey registration, login, and add."""
    return PASSKEY_DEMO_HTML
