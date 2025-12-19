const translations = {
    'en': {
        'nav_attendance': 'Attendance',
        'nav_my_attendance': 'My Attendance',
        'nav_dashboard': 'Dashboard',
        'nav_alerts': 'Alerts',
        'nav_register': 'Register Student',
        'nav_logout': 'Logout',
        'home_title': 'AI-Powered In-Plant Training Attendance',
        'home_subtitle': 'Secure, Geo-tagged, and Real-time attendance tracking for Industry 4.0',
        'btn_start_attendance': 'Start Attendance',
        'btn_view_dashboard': 'View Dashboard',
        'btn_my_attendance': 'My Attendance',
        'dash_total_students': 'Total Students',
        'dash_present_today': 'Present Today',
        'dash_anomalies': 'Anomalies',
        'dash_trends': 'Attendance Trends',
        'dash_quick_actions': 'Quick Actions',
        'btn_download_report': 'Download Report',
        'btn_manage_students': 'Manage Students',
        'btn_sync_portal': 'Sync with ITI Portal',
        'reg_title': 'Register New User',
        'reg_name': 'Full Name',
        'reg_role': 'Role',
        'reg_username': 'Username',
        'reg_password': 'Password',
        'btn_register': 'Register User',
        'btn_capture': 'Capture Face',
        'btn_retake': 'Retake',
        'loc_title': 'Your Location',
        'loc_lat': 'Latitude',
        'loc_long': 'Longitude',
        'loc_acc': 'Accuracy',
        'btn_force_refresh': 'Force Refresh Location',
        'status_ready': 'Ready to scan',
        'status_verifying': 'Verifying...',
        'alert_title': 'System Alerts',
        'alert_type': 'Type',
        'alert_desc': 'Description',
        'alert_risk': 'Risk Level',
        'alert_time': 'Time',
        'alert_status': 'Status',
        'alert_action': 'Action'
    },
    'te': {
        'nav_attendance': 'హాజరు',
        'nav_my_attendance': 'నా హాజరు',
        'nav_dashboard': 'డ్యాష్‌బోర్డ్',
        'nav_alerts': 'అలర్ట్‌లు',
        'nav_register': 'విద్యార్థి నమోదు',
        'nav_logout': 'లాగ్ అవుట్',
        'home_title': 'AI-ఆధారిత ఇన్-ప్లాంట్ శిక్షణ హాజరు',
        'home_subtitle': 'పరిశ్రమ 4.0 కోసం సురక్షితమైన, జియో-ట్యాగ్ చేయబడిన మరియు నిజ-సమయ హాజరు ట్రాకింగ్',
        'btn_start_attendance': 'హాజరు ప్రారంభించండి',
        'btn_view_dashboard': 'డ్యాష్‌బోర్డ్ చూడండి',
        'btn_my_attendance': 'నా హాజరు',
        'dash_total_students': 'మొత్తం విద్యార్థులు',
        'dash_present_today': 'నేడు హాజరైనవారు',
        'dash_anomalies': 'అసాధారణతలు',
        'dash_trends': 'హాజరు పోకడలు',
        'dash_quick_actions': 'త్వరిత చర్యలు',
        'btn_download_report': 'నివేదికను డౌన్‌లోడ్ చేయండి',
        'btn_manage_students': 'విద్యార్థులను నిర్వహించండి',
        'btn_sync_portal': 'ITI పోర్టల్‌తో సమకాలీకరించండి',
        'reg_title': 'కొత్త వినియోగదారుని నమోదు చేయండి',
        'reg_name': 'పూర్తి పేరు',
        'reg_role': 'పాత్ర',
        'reg_username': 'వినియోగదారు పేరు',
        'reg_password': 'పాస్‌వర్డ్',
        'btn_register': 'వినియోగదారుని నమోదు చేయండి',
        'btn_capture': 'ముఖాన్ని క్యాప్చర్ చేయండి',
        'btn_retake': 'మళ్ళీ తీసుకోండి',
        'loc_title': 'మీ స్థానం',
        'loc_lat': 'అక్షాంశం',
        'loc_long': 'రేఖాంశం',
        'loc_acc': 'ఖచ్చితత్వం',
        'btn_force_refresh': 'స్థానాన్ని రిఫ్రెష్ చేయండి',
        'status_ready': 'స్కాన్ చేయడానికి సిద్ధంగా ఉంది',
        'status_verifying': 'ధృవీకరిస్తోంది...',
        'alert_title': 'సిస్టమ్ అలర్ట్‌లు',
        'alert_type': 'రకం',
        'alert_desc': 'వివరణ',
        'alert_risk': 'ప్రమాద స్థాయి',
        'alert_time': 'సమయం',
        'alert_status': 'స్థితి',
        'alert_action': 'చర్య'
    }
};

function applyTranslations(lang) {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (translations[lang] && translations[lang][key]) {
            if (el.tagName === 'INPUT' && el.type === 'placeholder') {
                el.placeholder = translations[lang][key];
            } else {
                el.innerText = translations[lang][key];
            }
        }
    });
    localStorage.setItem('preferred_lang', lang);
}

document.addEventListener('DOMContentLoaded', () => {
    const savedLang = localStorage.getItem('preferred_lang') || 'en';
    applyTranslations(savedLang);
});
