<?php
$configFile = __DIR__ . '/config.php';
$config = file_exists($configFile) ? require $configFile : require __DIR__ . '/config.example.php';
$engineUrl = rtrim((string)($config['engine_url'] ?? ''), '/');
$dashboardToken = (string)($config['dashboard_token'] ?? '');
?>
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Raymond AI Command Center</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css" rel="stylesheet">
  <style>
    :root{--ink:#eaf0ff;--muted:#9eabc5;--panel:#111d35;--line:rgba(180,200,255,.14);--accent:#7c8cff}
    *{box-sizing:border-box} body{min-height:100vh;margin:0;color:var(--ink);font-family:Inter,system-ui,Segoe UI,sans-serif;background:radial-gradient(ellipse at 15% 5%,#253d72 0,transparent 38%),radial-gradient(ellipse at 90% 90%,#40265f 0,transparent 35%),#080f20}
    .shell{max-width:1100px;margin:auto;padding:34px 18px}.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:28px}.brand{display:flex;gap:13px;align-items:center}.brand-icon{width:46px;height:46px;border-radius:15px;display:grid;place-items:center;background:linear-gradient(135deg,#6885ff,#a15ee8);font-size:21px;box-shadow:0 10px 28px #566be855}.sub{color:var(--muted);font-size:13px}.status{border:1px solid var(--line);border-radius:30px;padding:8px 12px;color:#b9c7e3;font-size:12px}.panel{background:rgba(17,29,53,.91);border:1px solid var(--line);border-radius:22px;box-shadow:0 22px 70px #0005;overflow:hidden}.panel-head{padding:22px 24px;border-bottom:1px solid var(--line)}.conversation{min-height:360px;max-height:58vh;overflow:auto;padding:24px}.welcome{max-width:620px;margin:38px auto;text-align:center}.welcome .orb{width:66px;height:66px;margin:0 auto 18px;border-radius:22px;display:grid;place-items:center;background:linear-gradient(135deg,#657fff,#a05ce0);font-size:27px}.bubble{max-width:85%;padding:15px 17px;border-radius:17px;margin:0 0 15px;white-space:pre-wrap;line-height:1.55}.user{margin-left:auto;background:#354d91}.assistant{background:#1b2b49;border:1px solid var(--line)}.composer{padding:18px;border-top:1px solid var(--line);background:#0d172b}.composer textarea{background:#17243d;color:white;border:1px solid #344563;border-radius:14px;resize:vertical}.composer textarea:focus{background:#17243d;color:white;border-color:#8291ff;box-shadow:0 0 0 3px #8291ff22}.send{border:0;border-radius:13px;background:linear-gradient(135deg,#6885ff,#985fe4);color:white;padding:12px 20px;font-weight:700}.send:disabled{opacity:.55}.hint{color:var(--muted);font-size:12px}.tag{display:inline-block;border:1px solid var(--line);padding:6px 10px;border-radius:20px;color:#c2cdec;font-size:12px;margin:4px}
  </style>
</head>
<body>
<div class="shell">
  <header class="top">
    <div class="brand"><div class="brand-icon"><i class="fa-solid fa-wand-magic-sparkles"></i></div><div><div class="fw-bold fs-5">Raymond AI</div><div class="sub">Website command center</div></div></div>
    <div class="status"><i class="fa-solid fa-circle text-warning me-2" style="font-size:8px"></i><span id="connection">Checking engine…</span></div>
  </header>
  <main class="panel">
    <div class="panel-head d-flex justify-content-between align-items-center"><div><div class="fw-semibold">AI workspace</div><div class="sub">Describe what you want to build or change</div></div><span class="tag">InfinityFree deployment planned</span></div>
    <section class="conversation" id="conversation" aria-live="polite">
      <div class="welcome" id="welcome"><div class="orb"><i class="fa-solid fa-code"></i></div><h2 class="h4 fw-bold">What shall we build today?</h2><p class="sub">Write your instruction naturally. The connected engine will receive it and return its response.</p><div><span class="tag">Create a website</span><span class="tag">Update a project</span><span class="tag">Fix an error</span></div></div>
    </section>
    <form class="composer" id="commandForm">
      <div class="row g-2 align-items-end">
        <div class="col"><label class="form-label sub" for="command">Your command</label><textarea class="form-control" id="command" rows="3" maxlength="12000" placeholder="Example: Create a modern hotel website with rooms, booking, gallery and contact pages…" required></textarea></div>
        <div class="col-auto"><button class="send" id="send" type="submit"><i class="fa-solid fa-arrow-up me-1"></i> Send</button></div>
      </div>
      <div class="d-flex justify-content-between mt-2"><span class="hint">Do not enter passwords or API keys in chat messages.</span><span class="hint">Enter to send · Shift + Enter for new line</span></div>
    </form>
  </main>
  <p class="text-center sub mt-3">Raymond AI Command Center · Initial connection scaffold</p>
</div>
<script>
const ENGINE_URL = <?= json_encode($engineUrl) ?>;
const DASHBOARD_TOKEN = <?= json_encode($dashboardToken) ?>;
const conversation = document.getElementById('conversation');
const form = document.getElementById('commandForm');
const input = document.getElementById('command');
const send = document.getElementById('send');
const connection = document.getElementById('connection');
function addBubble(text, role){document.getElementById('welcome')?.remove();const el=document.createElement('div');el.className='bubble '+role;el.textContent=text;conversation.appendChild(el);conversation.scrollTop=conversation.scrollHeight;return el;}
async function checkEngine(){if(!ENGINE_URL || ENGINE_URL.includes('YOUR-RENDER-SERVICE')){connection.textContent='Engine URL not configured';return;}try{const r=await fetch(ENGINE_URL+'/health');if(!r.ok)throw new Error();connection.textContent='Engine online';}catch(e){connection.textContent='Engine unavailable';}}
form.addEventListener('submit',async e=>{e.preventDefault();const command=input.value.trim();if(!command)return;addBubble(command,'user');input.value='';send.disabled=true;send.innerHTML='<i class="fa-solid fa-spinner fa-spin me-1"></i> Working';const pending=addBubble('Sending your command to Raymond AI…','assistant');try{const r=await fetch(ENGINE_URL+'/command',{method:'POST',headers:{'Content-Type':'application/json','X-Dashboard-Token':DASHBOARD_TOKEN},body:JSON.stringify({command,project:'raymond-project'})});const data=await r.json();if(!r.ok)throw new Error(data.detail||'The engine returned an error.');pending.textContent=(data.status==='planning'?'Implementation plan (execution tools are not enabled yet):\n\n':'')+data.message;}catch(err){pending.textContent='Could not complete the request: '+err.message+'\n\nCheck that the Render engine is deployed and the dashboard configuration is correct.';}finally{send.disabled=false;send.innerHTML='<i class="fa-solid fa-arrow-up me-1"></i> Send';input.focus();}});
input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();form.requestSubmit();}});
checkEngine();
</script>
</body>
</html>
