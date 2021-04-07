
strava_auth_confirm_page = """
<html>
<head>
    <script src="https://code.iconify.design/1/1.0.7/iconify.min.js"></script>
    <title>Strava Authentication Successful!</title></head>
<style>
    body {{
        background-color: #F7F7Fa;
        font-family: -apple-system, system-ui, BlinkMacSystemFont, Roboto, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol';
        font-size: 14px;
        line-height: 1.3em;
        text-align: center;
    }}
    h1 {{
        font-size: 22px;
        font-weight: 400;
        line-height: 28px;
    }}
    .center-block {{
        background-color: #FFFFFF;
        max-width: 540px;
        padding: 40px;
        position: fixed;
        top: 50px;
        left: 50%;
        transform: translate(-50%, 0%)
    }}
    .strava {{
        color: #FC4C02;
        font-weight: 800;
    }}
    .iconify {{
        color: #FC4C02;
    }}
 }}
</style>
<body>
    <div class="center-block">
        <h1>{success_msg} with 
            <span class="iconify" data-icon="fa-brands:strava" data-inline="false"></span>
            <span class="strava">STRAVA</span>.</h1>
        <p>{action_msg}</p>
    </div>
</body>
</html>
"""
