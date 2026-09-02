import subprocess, json, time, sys

p = subprocess.Popen(['uvx', 'mcp-pdf'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def send(msg):
    p.stdin.write((json.dumps(msg) + '\n').encode())
    p.stdin.flush()

def read_until_id(target_id, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        line = p.stdout.readline().decode('utf-8', errors='replace').strip()
        if not line or not line.startswith('{'):
            continue
        try:
            d = json.loads(line)
            if d.get('id') == target_id:
                return d
        except: pass
    return None

# Initialize
send({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'test','version':'1.0'}}})
r = read_until_id(1)
print('Init: ' + ('OK' if r else 'FAIL'), flush=True)
send({'jsonrpc':'2.0','method':'notifications/initialized','params':{}})

# 14 tool calls - same tool, different ID each time
for i in range(2, 16):
    send({'jsonrpc':'2.0','id':i,'method':'tools/call','params':{'name':'contentanalysis__analyze_layout','arguments':{'pdf_path':'curriculum/01_simple_text_helvetica.pdf'}}})
    r = read_until_id(i, timeout=8)
    status = 'OK' if r and 'result' in r else ('ERROR' if r and 'error' in r else 'TIMEOUT')
    print('[' + str(i) + '] ' + status, flush=True)
    if status == 'TIMEOUT':
        stderr_data = p.stderr.read(4096).decode('utf-8', errors='replace')
        # filter to just the last few lines
        lines = stderr_data.strip().split('\n')
        for line in lines[-10:]:
            print('  STDERR: ' + line, flush=True)
        break

p.terminate()
p.wait()
print('Done', flush=True)
