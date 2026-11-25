"""CTF practice machines and platforms for GHOSTPATH X v0.3 (lab only).

Static curated catalogue: free / free-tier places to download vulnerable
VMs or practise online. Homepage URLs are homepage-level only and were
HTTP-checked when this list was built (see the report that shipped with
it). No prices are invented: a source that is free-tier-only is labelled
"Free tier" or "Free + paid", never plain "Free".

CyberSecLabs is deliberately NOT listed: its site did not resolve on
either https://cyberseclabs.co.uk/ or https://www.cyberseclabs.co.uk/
and the company behind it was dissolved in April 2024, so shipping
its link would ship a broken link.
"""

SAFETY_NOTE = (
    "Only attack systems you own or have explicit permission to test. "
    "Run downloaded VMs on Host-Only networking, never bridged to your "
    "home LAN. VulnHub itself warns it cannot check every machine."
)

# In-memory solved flags, same pattern as the app's in-memory store.
SOLVED_IDS: set[str] = set()

_VULNHUB_SETUP = [
    "Download the .ova/.zip from VulnHub (use the homepage link).",
    "Import it into VirtualBox (File > Import Appliance).",
    "Set the VM network to Host-Only so it can only talk to your Kali VM, never your home LAN.",
    "Boot the VM, then find its IP from Kali with nmap (e.g. nmap -sn <host-only-subnet>/24).",
]

MACHINES: list[dict] = [
    # -- VulnHub: 100% free downloadable VMs, offline ------------------
    {
        "id": "vulnhub-mr-robot-1",
        "name": "Mr-Robot: 1",
        "source": "VulnHub",
        "type": "downloadable VM",
        "cost_label": "Free",
        "difficulty": "Intermediate",
        "topics": ["web", "WordPress", "privilege escalation", "enumeration"],
        "os": "Linux",
        "format": "OVA",
        "homepage_url": "https://www.vulnhub.com/",
        "description": (
            "The classic beginner-to-intermediate VM based on the Mr. Robot "
            "TV show: enumerate a WordPress site, find the hidden keys, "
            "and escalate to root."
        ),
        "setup_steps": _VULNHUB_SETUP,
        "learnings": ["WordPress enumeration", "hidden file discovery", "Linux privilege escalation"],
    },
    {
        "id": "vulnhub-dc-1",
        "name": "DC-1",
        "source": "VulnHub",
        "type": "downloadable VM",
        "cost_label": "Free",
        "difficulty": "Beginner",
        "topics": ["Drupal", "SUID", "privilege escalation", "enumeration"],
        "os": "Linux",
        "format": "OVA",
        "homepage_url": "https://www.vulnhub.com/",
        "description": (
            "A beginner-friendly Drupal VM: exploit the CMS to get a shell, "
            "then abuse a SUID binary to become root."
        ),
        "setup_steps": _VULNHUB_SETUP,
        "learnings": ["Drupal exploitation", "SUID privilege escalation", "basic enumeration"],
    },
    {
        "id": "vulnhub-dc-2",
        "name": "DC-2",
        "source": "VulnHub",
        "type": "downloadable VM",
        "cost_label": "Free",
        "difficulty": "Beginner",
        "topics": ["WordPress", "privilege escalation", "enumeration"],
        "os": "Linux",
        "format": "OVA",
        "homepage_url": "https://www.vulnhub.com/",
        "description": (
            "A WordPress VM with a twist: the flags point you at the next "
            "step, so it teaches the methodology as well as the exploit."
        ),
        "setup_steps": _VULNHUB_SETUP,
        "learnings": ["WordPress enumeration", "credential reuse", "Linux privilege escalation"],
    },
    {
        "id": "vulnhub-dc-3",
        "name": "DC-3",
        "source": "VulnHub",
        "type": "downloadable VM",
        "cost_label": "Free",
        "difficulty": "Intermediate",
        "topics": ["Joomla", "privilege escalation", "enumeration"],
        "os": "Linux",
        "format": "OVA",
        "homepage_url": "https://www.vulnhub.com/",
        "description": (
            "A Joomla VM: find the SQL injection in the CMS, get a shell, "
            "and escalate to root."
        ),
        "setup_steps": _VULNHUB_SETUP,
        "learnings": ["Joomla exploitation", "SQL injection", "Linux privilege escalation"],
    },
    {
        "id": "vulnhub-kioptrix-1",
        "name": "Kioptrix Level 1",
        "source": "VulnHub",
        "type": "downloadable VM",
        "cost_label": "Free",
        "difficulty": "Beginner",
        "topics": ["Samba", "Apache", "enumeration"],
        "os": "Linux",
        "format": "OVA",
        "homepage_url": "https://www.vulnhub.com/",
        "description": (
            "One of the oldest beginner VMs: enumerate Samba and Apache, "
            "exploit a known service flaw, and get root."
        ),
        "setup_steps": _VULNHUB_SETUP,
        "learnings": ["service enumeration", "Samba exploitation", "known-vulnerability research"],
    },
    {
        "id": "vulnhub-kioptrix-2",
        "name": "Kioptrix Level 2",
        "source": "VulnHub",
        "type": "downloadable VM",
        "cost_label": "Free",
        "difficulty": "Beginner",
        "topics": ["web", "privilege escalation", "enumeration"],
        "os": "Linux",
        "format": "OVA",
        "homepage_url": "https://www.vulnhub.com/",
        "description": (
            "The second Kioptrix level: web enumeration leads to a shell, "
            "and a kernel flaw leads to root."
        ),
        "setup_steps": _VULNHUB_SETUP,
        "learnings": ["web enumeration", "shell upgrading", "kernel privilege escalation"],
    },
    {
        "id": "vulnhub-kioptrix-3",
        "name": "Kioptrix Level 3",
        "source": "VulnHub",
        "type": "downloadable VM",
        "cost_label": "Free",
        "difficulty": "Intermediate",
        "topics": ["web", "privilege escalation", "enumeration"],
        "os": "Linux",
        "format": "OVA",
        "homepage_url": "https://www.vulnhub.com/",
        "description": (
            "A step up from Level 2: deeper web work and a less obvious "
            "path to root."
        ),
        "setup_steps": _VULNHUB_SETUP,
        "learnings": ["web exploitation", "manual enumeration", "Linux privilege escalation"],
    },
    {
        "id": "vulnhub-kioptrix-4",
        "name": "Kioptrix Level 4",
        "source": "VulnHub",
        "type": "downloadable VM",
        "cost_label": "Free",
        "difficulty": "Intermediate",
        "topics": ["web", "SQL injection", "privilege escalation"],
        "os": "Linux",
        "format": "OVA",
        "homepage_url": "https://www.vulnhub.com/",
        "description": (
            "The final Kioptrix level: SQL injection and web flaws open the "
            "door, then privilege escalation finishes the job."
        ),
        "setup_steps": _VULNHUB_SETUP,
        "learnings": ["SQL injection", "web exploitation", "Linux privilege escalation"],
    },
    {
        "id": "vulnhub-basic-pentesting-1",
        "name": "Basic Pentesting: 1",
        "source": "VulnHub",
        "type": "downloadable VM",
        "cost_label": "Free",
        "difficulty": "Beginner",
        "topics": ["FTP", "SSH", "privilege escalation", "enumeration"],
        "os": "Linux",
        "format": "OVA",
        "homepage_url": "https://www.vulnhub.com/",
        "description": (
            "A true first VM: FTP, SSH and a weak password lead to a shell, "
            "then a simple privilege escalation to root."
        ),
        "setup_steps": _VULNHUB_SETUP,
        "learnings": ["FTP and SSH enumeration", "weak credentials", "basic privilege escalation"],
    },
    {
        "id": "vulnhub-basic-pentesting-2",
        "name": "Basic Pentesting: 2",
        "source": "VulnHub",
        "type": "downloadable VM",
        "cost_label": "Free",
        "difficulty": "Beginner",
        "topics": ["web", "SSH", "privilege escalation", "enumeration"],
        "os": "Linux",
        "format": "OVA",
        "homepage_url": "https://www.vulnhub.com/",
        "description": (
            "The sequel to Basic Pentesting: 1 — a little more web work "
            "before the shell and the escalation."
        ),
        "setup_steps": _VULNHUB_SETUP,
        "learnings": ["web enumeration", "SSH exploitation", "Linux privilege escalation"],
    },
    {
        "id": "vulnhub-sickos-1-1",
        "name": "SickOs 1.1",
        "source": "VulnHub",
        "type": "downloadable VM",
        "cost_label": "Free",
        "difficulty": "Intermediate",
        "topics": ["web", "privilege escalation", "enumeration"],
        "os": "Linux",
        "format": "OVA",
        "homepage_url": "https://www.vulnhub.com/",
        "description": (
            "An intermediate VM where web enumeration and a misconfigured "
            "service lead to a shell and root."
        ),
        "setup_steps": _VULNHUB_SETUP,
        "learnings": ["web enumeration", "service misconfiguration", "Linux privilege escalation"],
    },
    {
        "id": "vulnhub-funbox-scriptkiddie",
        "name": "Funbox: Scriptkiddie",
        "source": "VulnHub",
        "type": "downloadable VM",
        "cost_label": "Free",
        "difficulty": "Beginner",
        "topics": ["web", "privilege escalation", "enumeration"],
        "os": "Linux",
        "format": "OVA",
        "homepage_url": "https://www.vulnhub.com/",
        "description": (
            "A fun beginner box from the Funbox series: enumerate the web "
            "app, get a shell, and escalate."
        ),
        "setup_steps": _VULNHUB_SETUP,
        "learnings": ["web enumeration", "shell access", "Linux privilege escalation"],
    },
    {
        "id": "vulnhub-skytower-1",
        "name": "SkyTower: 1",
        "source": "VulnHub",
        "type": "downloadable VM",
        "cost_label": "Free",
        "difficulty": "Intermediate",
        "topics": ["web", "SQL injection", "privilege escalation"],
        "os": "Linux",
        "format": "OVA",
        "homepage_url": "https://www.vulnhub.com/",
        "description": (
            "An intermediate VM built around a web app: SQL injection and "
            "credential reuse lead to root."
        ),
        "setup_steps": _VULNHUB_SETUP,
        "learnings": ["SQL injection", "credential reuse", "Linux privilege escalation"],
    },
    {
        "id": "vulnhub-fristileaks-1-3",
        "name": "Fristileaks 1.3",
        "source": "VulnHub",
        "type": "downloadable VM",
        "cost_label": "Free",
        "difficulty": "Intermediate",
        "topics": ["web", "Python", "privilege escalation", "enumeration"],
        "os": "Linux",
        "format": "OVA",
        "homepage_url": "https://www.vulnhub.com/",
        "description": (
            "An intermediate web-focused VM: a leaked login and a Python "
            "privilege-escalation path to root."
        ),
        "setup_steps": _VULNHUB_SETUP,
        "learnings": ["web enumeration", "Python privilege escalation", "patience with rabbit holes"],
    },
    # -- HackTheBox: free tier, online VPN lab (NOT a VM download) -----
    {
        "id": "htb-starting-point",
        "name": "Starting Point",
        "source": "HackTheBox",
        "type": "online lab",
        "cost_label": "Free tier",
        "difficulty": "Beginner",
        "topics": ["guided", "enumeration", "web", "privilege escalation"],
        "os": "Linux",
        "format": "Online",
        "homepage_url": "https://www.hackthebox.com/",
        "description": (
            "HackTheBox's free guided track: a series of easy machines with "
            "step-by-step walkthroughs, made for absolute beginners."
        ),
        "setup_steps": [
            "Create a free HackTheBox account.",
            "Download the OpenVPN file from the site and connect from Kali.",
            "Work through the Starting Point machines in order — each one teaches one skill.",
        ],
        "learnings": ["VPN lab workflow", "guided enumeration", "basic exploitation"],
    },
    {
        "id": "htb-lame",
        "name": "Lame",
        "source": "HackTheBox",
        "type": "online lab",
        "cost_label": "Free tier",
        "difficulty": "Beginner",
        "topics": ["Samba", "Metasploit", "enumeration"],
        "os": "Linux",
        "format": "Online",
        "homepage_url": "https://www.hackthebox.com/",
        "description": (
            "Example machine — rotating active machine, check the site for "
            "the current list. Lame is the classic first HackTheBox box: "
            "an old Samba service exploited with Metasploit."
        ),
        "setup_steps": [
            "Create a free HackTheBox account and connect with the OpenVPN file.",
            "Check the site for the currently active machines — the list rotates.",
            "Enumerate the target with nmap, then research the service version.",
        ],
        "learnings": ["Samba enumeration", "Metasploit basics", "service-version research"],
    },
    {
        "id": "htb-blue",
        "name": "Blue",
        "source": "HackTheBox",
        "type": "online lab",
        "cost_label": "Free tier",
        "difficulty": "Beginner",
        "topics": ["SMB", "EternalBlue", "Metasploit"],
        "os": "Windows",
        "format": "Online",
        "homepage_url": "https://www.hackthebox.com/",
        "description": (
            "Example machine — rotating active machine, check the site for "
            "the current list. Blue teaches the EternalBlue SMB flaw on a "
            "Windows target."
        ),
        "setup_steps": [
            "Create a free HackTheBox account and connect with the OpenVPN file.",
            "Check the site for the currently active machines — the list rotates.",
            "Enumerate SMB with nmap, then research the EternalBlue flaw.",
        ],
        "learnings": ["SMB enumeration", "Windows exploitation", "EternalBlue"],
    },
    {
        "id": "htb-legacy",
        "name": "Legacy",
        "source": "HackTheBox",
        "type": "online lab",
        "cost_label": "Free tier",
        "difficulty": "Beginner",
        "topics": ["SMB", "enumeration", "Metasploit"],
        "os": "Windows",
        "format": "Online",
        "homepage_url": "https://www.hackthebox.com/",
        "description": (
            "Example machine — rotating active machine, check the site for "
            "the current list. Legacy is a beginner Windows box built "
            "around old SMB services."
        ),
        "setup_steps": [
            "Create a free HackTheBox account and connect with the OpenVPN file.",
            "Check the site for the currently active machines — the list rotates.",
            "Enumerate SMB with nmap and look up the old service flaws.",
        ],
        "learnings": ["SMB enumeration", "Windows basics", "known-vulnerability research"],
    },
    # -- TryHackMe: free tier, guided rooms -----------------------------
    {
        "id": "tryhackme-pre-security",
        "name": "Pre Security",
        "source": "TryHackMe",
        "type": "online lab",
        "cost_label": "Free tier",
        "difficulty": "Beginner",
        "topics": ["networking", "Linux", "web", "basics"],
        "os": "Linux",
        "format": "Online",
        "homepage_url": "https://tryhackme.com/",
        "description": (
            "TryHackMe's free starting path: networking, Linux and web "
            "basics before you touch a real attack."
        ),
        "setup_steps": [
            "Create a free TryHackMe account.",
            "Open the Pre Security path and work through the rooms in order.",
            "Use the in-browser AttackBox or connect your own Kali over VPN.",
        ],
        "learnings": ["networking basics", "Linux basics", "how the web works"],
    },
    {
        "id": "tryhackme-jr-penetration-tester",
        "name": "Jr Penetration Tester",
        "source": "TryHackMe",
        "type": "online lab",
        "cost_label": "Free tier",
        "difficulty": "Beginner",
        "topics": ["penetration testing", "enumeration", "web", "privilege escalation"],
        "os": "Linux",
        "format": "Online",
        "homepage_url": "https://tryhackme.com/",
        "description": (
            "TryHackMe's free guided penetration-testing path: enumeration, "
            "web attacks and privilege escalation, room by room."
        ),
        "setup_steps": [
            "Create a free TryHackMe account.",
            "Open the Jr Penetration Tester path and work through the rooms in order.",
            "Use the in-browser AttackBox or connect your own Kali over VPN.",
        ],
        "learnings": ["penetration-testing methodology", "enumeration", "web attacks", "privilege escalation"],
    },
    {
        "id": "tryhackme-owasp-top-10",
        "name": "OWASP Top 10",
        "source": "TryHackMe",
        "type": "online lab",
        "cost_label": "Free tier",
        "difficulty": "Beginner",
        "topics": ["OWASP Top 10", "web", "SQL injection", "XSS"],
        "os": "Web",
        "format": "Online",
        "homepage_url": "https://tryhackme.com/",
        "description": (
            "A free guided room walking through each OWASP Top 10 risk "
            "with a live vulnerable app to practise on."
        ),
        "setup_steps": [
            "Create a free TryHackMe account.",
            "Open the OWASP Top 10 room and start the target machine.",
            "Read each task, then exploit that vulnerability in the live app.",
        ],
        "learnings": ["OWASP Top 10", "SQL injection", "XSS", "broken access control"],
    },
    {
        "id": "tryhackme-nmap",
        "name": "Nmap",
        "source": "TryHackMe",
        "type": "online lab",
        "cost_label": "Free tier",
        "difficulty": "Beginner",
        "topics": ["nmap", "enumeration", "networking"],
        "os": "Linux",
        "format": "Online",
        "homepage_url": "https://tryhackme.com/",
        "description": (
            "A free guided room that teaches nmap from the first scan to "
            "service detection and scripting."
        ),
        "setup_steps": [
            "Create a free TryHackMe account.",
            "Open the Nmap room and start the target machine.",
            "Follow the tasks, running each nmap scan yourself from Kali or the AttackBox.",
        ],
        "learnings": ["nmap scanning", "service detection", "enumeration workflow"],
    },
    {
        "id": "tryhackme-linux-fundamentals",
        "name": "Linux Fundamentals",
        "source": "TryHackMe",
        "type": "online lab",
        "cost_label": "Free tier",
        "difficulty": "Beginner",
        "topics": ["Linux", "terminal", "basics"],
        "os": "Linux",
        "format": "Online",
        "homepage_url": "https://tryhackme.com/",
        "description": (
            "A free guided room covering the Linux terminal, files, "
            "permissions and processes — the groundwork for everything else."
        ),
        "setup_steps": [
            "Create a free TryHackMe account.",
            "Open the Linux Fundamentals room and start the target machine.",
            "Type every command yourself instead of copying the answers.",
        ],
        "learnings": ["Linux terminal", "file permissions", "processes and services"],
    },
    # -- PortSwigger Web Security Academy: 100% free web labs ----------
    {
        "id": "portswigger-sqli-labs",
        "name": "SQL Injection Labs",
        "source": "PortSwigger Web Security Academy",
        "type": "web app",
        "cost_label": "Free",
        "difficulty": "Beginner",
        "topics": ["SQL injection", "web", "database"],
        "os": "Web",
        "format": "Online",
        "homepage_url": "https://portswigger.net/web-security",
        "description": (
            "Free interactive SQL injection labs from PortSwigger: learn "
            "each technique, then solve the lab in the browser."
        ),
        "setup_steps": [
            "Create a free PortSwigger account.",
            "Open the SQL injection topic and read the explanation.",
            "Click into a lab and solve it in the browser — no setup needed.",
        ],
        "learnings": ["SQL injection", "UNION attacks", "blind SQL injection"],
    },
    {
        "id": "portswigger-xss-labs",
        "name": "Cross-Site Scripting (XSS) Labs",
        "source": "PortSwigger Web Security Academy",
        "type": "web app",
        "cost_label": "Free",
        "difficulty": "Beginner",
        "topics": ["XSS", "web", "JavaScript"],
        "os": "Web",
        "format": "Online",
        "homepage_url": "https://portswigger.net/web-security",
        "description": (
            "Free interactive XSS labs from PortSwigger: reflected, stored "
            "and DOM-based cross-site scripting, each with a live lab."
        ),
        "setup_steps": [
            "Create a free PortSwigger account.",
            "Open the XSS topic and read the explanation.",
            "Click into a lab and solve it in the browser — no setup needed.",
        ],
        "learnings": ["reflected XSS", "stored XSS", "DOM-based XSS"],
    },
    {
        "id": "portswigger-auth-labs",
        "name": "Authentication & Access Control Labs",
        "source": "PortSwigger Web Security Academy",
        "type": "web app",
        "cost_label": "Free",
        "difficulty": "Intermediate",
        "topics": ["authentication", "access control", "web", "SSRF"],
        "os": "Web",
        "format": "Online",
        "homepage_url": "https://portswigger.net/web-security",
        "description": (
            "Free interactive labs on authentication bypass, broken access "
            "control and SSRF from PortSwigger."
        ),
        "setup_steps": [
            "Create a free PortSwigger account.",
            "Open the authentication or access-control topic and read the explanation.",
            "Click into a lab and solve it in the browser — no setup needed.",
        ],
        "learnings": ["authentication bypass", "broken access control", "SSRF"],
    },
    # -- OverTheWire: 100% free SSH wargames ----------------------------
    {
        "id": "overthewire-bandit",
        "name": "Bandit",
        "source": "OverTheWire",
        "type": "wargame",
        "cost_label": "Free",
        "difficulty": "Beginner",
        "topics": ["Linux", "SSH", "terminal", "basics"],
        "os": "Linux",
        "format": "Online",
        "homepage_url": "https://overthewire.org/",
        "description": (
            "The classic free SSH wargame for Linux beginners: each level "
            "teaches one command or idea, and its password unlocks the next."
        ),
        "setup_steps": [
            "Open a terminal on Kali.",
            "SSH in with: ssh bandit0@bandit.labs.overthewire.org -p 2220 (password bandit0).",
            "Read the level goal on the site, solve it, and use the password you find for the next level.",
        ],
        "learnings": ["Linux terminal", "SSH", "files and permissions"],
    },
    # -- PicoCTF: 100% free ---------------------------------------------
    {
        "id": "picoctf",
        "name": "PicoCTF",
        "source": "PicoCTF",
        "type": "wargame",
        "cost_label": "Free",
        "difficulty": "Beginner",
        "topics": ["web", "cryptography", "forensics", "reverse engineering"],
        "os": "Web",
        "format": "Online",
        "homepage_url": "https://picoctf.org/",
        "description": (
            "A free beginner-friendly CTF run by Carnegie Mellon: web, "
            "crypto, forensics and reverse-engineering challenges that stay "
            "open for practice all year."
        ),
        "setup_steps": [
            "Create a free PicoCTF account.",
            "Pick the practice challenges and start with the easiest ones.",
            "Solve in your browser and terminal — no download needed.",
        ],
        "learnings": ["web exploitation", "cryptography basics", "forensics", "reverse engineering"],
    },
    # -- Root-Me: free tier ---------------------------------------------
    {
        "id": "root-me",
        "name": "Root-Me Challenges",
        "source": "Root-Me",
        "type": "online lab",
        "cost_label": "Free tier",
        "difficulty": "Beginner",
        "topics": ["web", "cryptography", "forensics", "networking"],
        "os": "Web",
        "format": "Online",
        "homepage_url": "https://www.root-me.org/",
        "description": (
            "A large free-tier challenge platform: most challenges are "
            "free, covering web, crypto, forensics, networking and more."
        ),
        "setup_steps": [
            "Create a free Root-Me account.",
            "Start with the beginner web challenges.",
            "Solve in your browser — most challenges need no download.",
        ],
        "learnings": ["web exploitation", "cryptography", "forensics", "enumeration"],
    },
    # -- Metasploitable: free downloadable VMs --------------------------
    {
        "id": "metasploitable-2",
        "name": "Metasploitable 2",
        "source": "Metasploitable",
        "type": "downloadable VM",
        "cost_label": "Free",
        "difficulty": "Beginner",
        "topics": ["Metasploit", "FTP", "Samba", "web", "privilege escalation"],
        "os": "Linux",
        "format": "ZIP",
        "homepage_url": "https://docs.rapid7.com/metasploit/metasploitable-2/",
        "description": (
            "Rapid7's intentionally vulnerable Ubuntu VM, built for learning "
            "Metasploit: over 20 vulnerable services in one target."
        ),
        "setup_steps": [
            "Download the .zip from the Rapid7 docs page (SourceForge link).",
            "Extract it and import the virtual disk into VirtualBox or VMware.",
            "Set the VM network to Host-Only — never bridged, this VM is wide open.",
            "Log in with msfadmin / msfadmin and attack it from Kali with nmap and Metasploit.",
        ],
        "learnings": ["Metasploit basics", "vulnerable-service exploitation", "nmap enumeration"],
    },
    {
        "id": "metasploitable-3",
        "name": "Metasploitable 3",
        "source": "Metasploitable",
        "type": "downloadable VM",
        "cost_label": "Free",
        "difficulty": "Intermediate",
        "topics": ["Windows", "Active Directory", "Metasploit", "privilege escalation"],
        "os": "Windows",
        "format": "OVA",
        "homepage_url": "https://github.com/rapid7/metasploitable3",
        "description": (
            "Rapid7's Windows vulnerable VM, built with Packer and Vagrant: "
            "a newer Windows target with Active Directory-style flaws."
        ),
        "setup_steps": [
            "Clone the rapid7/metasploitable3 repo and build it with Packer/Vagrant, or use a prebuilt box.",
            "Import the VM into VirtualBox or VMware.",
            "Set the VM network to Host-Only — never bridged, this VM is wide open.",
            "Attack it from Kali with nmap and Metasploit.",
        ],
        "learnings": ["Windows exploitation", "Active Directory basics", "Metasploit on Windows"],
    },
    # -- OWASP vulnerable web apps: free, Docker ------------------------
    {
        "id": "owasp-dvwa",
        "name": "Damn Vulnerable Web Application (DVWA)",
        "source": "DVWA",
        "type": "web app",
        "cost_label": "Free",
        "difficulty": "Beginner",
        "topics": ["SQL injection", "XSS", "web", "OWASP Top 10"],
        "os": "Web",
        "format": "Docker",
        "homepage_url": "https://github.com/digininja/DVWA",
        "description": (
            "A deliberately vulnerable PHP/MySQL web app with a difficulty "
            "slider: start on Low, then raise it as you learn."
        ),
        "setup_steps": [
            "Run the official Docker image (see the repo README).",
            "Open it in your browser and log in with admin / password.",
            "Set the security level to Low first, then raise it as you improve.",
        ],
        "learnings": ["SQL injection", "XSS", "OWASP Top 10", "difficulty progression"],
    },
    {
        "id": "owasp-juice-shop",
        "name": "OWASP Juice Shop",
        "source": "OWASP Juice Shop",
        "type": "web app",
        "cost_label": "Free",
        "difficulty": "Beginner",
        "topics": ["web", "OWASP Top 10", "SQL injection", "XSS"],
        "os": "Web",
        "format": "Docker",
        "homepage_url": "https://owasp.org/www-project-juice-shop/",
        "description": (
            "The most popular intentionally vulnerable shop app: find the "
            "OWASP Top 10 flaws in a modern-looking online store."
        ),
        "setup_steps": [
            "Run the official Docker image (see the project page).",
            "Open http://localhost:3000 in your browser.",
            "Work through the score board challenges from easiest to hardest.",
        ],
        "learnings": ["OWASP Top 10", "modern web attacks", "score-board challenge flow"],
    },
    {
        "id": "owasp-webgoat",
        "name": "OWASP WebGoat",
        "source": "OWASP WebGoat",
        "type": "web app",
        "cost_label": "Free",
        "difficulty": "Intermediate",
        "topics": ["web", "OWASP Top 10", "lessons", "secure coding"],
        "os": "Web",
        "format": "Docker",
        "homepage_url": "https://owasp.org/www-project-webgoat/",
        "description": (
            "OWASP's lesson-based vulnerable app: each lesson explains a "
            "flaw, then asks you to exploit it and fix it."
        ),
        "setup_steps": [
            "Run the official Docker image (see the project page).",
            "Open it in your browser and register a local account.",
            "Work through the lessons in order — each one teaches then tests.",
        ],
        "learnings": ["OWASP Top 10", "exploit then fix", "secure-coding mindset"],
    },
    {
        "id": "owasp-bwapp",
        "name": "bWAPP (buggy web application)",
        "source": "bWAPP",
        "type": "web app",
        "cost_label": "Free",
        "difficulty": "Beginner",
        "topics": ["web", "SQL injection", "XSS", "OWASP Top 10"],
        "os": "Web",
        "format": "Docker",
        "homepage_url": "https://github.com/lmoroz/bWAPP",
        "description": (
            "A buggy web app with over 100 web vulnerabilities. The link is "
            "a community Docker-bundled fork — the original repo is no "
            "longer on GitHub."
        ),
        "setup_steps": [
            "Clone the repo and start it with docker-compose up -d.",
            "Open the install page in your browser and click install.",
            "Log in with bee / bug and pick a bug to practise.",
        ],
        "learnings": ["100+ web bugs", "SQL injection", "XSS", "OWASP Top 10"],
    },
]

# IDs must be unique — fail loudly at import rather than shipping dupes.
_ids = [m["id"] for m in MACHINES]
if len(_ids) != len(set(_ids)):
    raise ValueError("duplicate ctf machine id in ctf_machines.machines")

SOURCES: list[dict] = [
    {
        "name": "VulnHub",
        "cost_label": "Free",
        "type": "downloadable VM",
        "homepage_url": "https://www.vulnhub.com/",
        "description": "100% free downloadable vulnerable VMs, offline, for VirtualBox/VMware.",
    },
    {
        "name": "HackTheBox",
        "cost_label": "Free tier",
        "type": "online lab",
        "homepage_url": "https://www.hackthebox.com/",
        "description": "Free tier with Starting Point and rotating active machines; VIP is paid. Online VPN lab, not a VM download.",
    },
    {
        "name": "TryHackMe",
        "cost_label": "Free tier",
        "type": "online lab",
        "homepage_url": "https://tryhackme.com/",
        "description": "Guided beginner rooms and paths; free tier with paid rooms on top.",
    },
    {
        "name": "PortSwigger Web Security Academy",
        "cost_label": "Free",
        "type": "web app",
        "homepage_url": "https://portswigger.net/web-security",
        "description": "100% free interactive web labs: SQLi, XSS, SSRF, auth bypass and more.",
    },
    {
        "name": "OverTheWire",
        "cost_label": "Free",
        "type": "wargame",
        "homepage_url": "https://overthewire.org/",
        "description": "100% free SSH wargames — start with Bandit.",
    },
    {
        "name": "PicoCTF",
        "cost_label": "Free",
        "type": "wargame",
        "homepage_url": "https://picoctf.org/",
        "description": "100% free CTF: web, crypto, forensics and reverse engineering.",
    },
    {
        "name": "Root-Me",
        "cost_label": "Free tier",
        "type": "online lab",
        "homepage_url": "https://www.root-me.org/",
        "description": "Free tier — most challenges are free — across web, crypto, forensics and networking.",
    },
    {
        "name": "Metasploitable",
        "cost_label": "Free",
        "type": "downloadable VM",
        "homepage_url": "https://docs.rapid7.com/metasploit/metasploitable-2/",
        "description": "Rapid7's free intentionally vulnerable VMs for learning Metasploit (2 is Linux, 3 is Windows).",
    },
    {
        "name": "DVWA",
        "cost_label": "Free",
        "type": "web app",
        "homepage_url": "https://github.com/digininja/DVWA",
        "description": "Free open-source vulnerable web app with a difficulty slider.",
    },
    {
        "name": "OWASP Juice Shop",
        "cost_label": "Free",
        "type": "web app",
        "homepage_url": "https://owasp.org/www-project-juice-shop/",
        "description": "Free open-source vulnerable shop app covering the OWASP Top 10.",
    },
    {
        "name": "OWASP WebGoat",
        "cost_label": "Free",
        "type": "web app",
        "homepage_url": "https://owasp.org/www-project-webgoat/",
        "description": "Free open-source lesson-based vulnerable app: exploit each flaw, then fix it.",
    },
    {
        "name": "bWAPP",
        "cost_label": "Free",
        "type": "web app",
        "homepage_url": "https://github.com/lmoroz/bWAPP",
        "description": "Free open-source buggy web app with 100+ vulnerabilities (Docker-bundled fork).",
    },
]


# -- helpers ----------------------------------------------------------
def public_machine(machine: dict) -> dict:
    """One machine as the API returns it, with its solved flag."""
    return {**machine, "solved": machine["id"] in SOLVED_IDS}


def get_machine(machine_id: str) -> dict | None:
    """One machine by id, or None."""
    for machine in MACHINES:
        if machine["id"] == machine_id:
            return public_machine(machine)
    return None


def list_machines(
    source: str | None = None,
    difficulty: str | None = None,
    machine_type: str | None = None,
    q: str | None = None,
) -> list[dict]:
    """Machines with optional filters. source/difficulty/type match
    case-insensitively and exactly; q is a case-insensitive substring
    over name, description and topics."""
    results = MACHINES
    if source:
        wanted = source.strip().lower()
        results = [m for m in results if m["source"].lower() == wanted]
    if difficulty:
        wanted = difficulty.strip().lower()
        results = [m for m in results if m["difficulty"].lower() == wanted]
    if machine_type:
        wanted = machine_type.strip().lower()
        results = [m for m in results if m["type"].lower() == wanted]
    if q:
        needle = q.strip().lower()
        results = [
            m
            for m in results
            if needle in m["name"].lower()
            or needle in m["description"].lower()
            or needle in " ".join(m["topics"]).lower()
        ]
    return [public_machine(m) for m in results]


def list_sources() -> list[dict]:
    """Platform list (copies, so callers cannot mutate the catalogue)."""
    return [dict(s) for s in SOURCES]


def mark_solved(machine_id: str, solved: bool) -> dict | None:
    """Set or clear a machine's solved flag; None if the id is unknown."""
    if get_machine(machine_id) is None:
        return None
    if solved:
        SOLVED_IDS.add(machine_id)
    else:
        SOLVED_IDS.discard(machine_id)
    return get_machine(machine_id)
