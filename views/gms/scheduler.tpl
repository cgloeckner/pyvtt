%today = datetime.date.today()
%now = datetime.datetime.now().time()
%number_formatter = lambda n: '0{0}'.format(n) if n < 10 else n
<div id="schedule">
    <img class="close" src="/static/close.png" onClick="hideSchedule();" draggable="false" title="CANCEL" />
    <h1>SCHEDULE GAME</h1>
    <form>
        <input type="hidden" id="gm_url" value="{{gm.url}}" />
        <input type="hidden" id="server" value="{{server}}" />
        <p>DATE:
            <select id="day" onChange="updateCountdown()">
%max_days = calendar.monthrange(today.year, today.month)[1]
%for value in range(max_days):
    %selected = ' selected' if today.day == value+1 else ''
                <option value="{{value+1}}"{{selected}}>{{number_formatter(value+1)}}</option>
%end
            </select>
            <select id="month" onChange="updateDays(); updateCountdown()">
%for value in range(12):
    %selected = ' selected' if today.month == value+1 else ''
                <option value="{{value+1}}"{{selected}}>{{calendar.month_name[value+1].upper()}}</option>
%end
            </select>
            <input type="number" id="year" value="{{today.year}}" onChange="updateDays(); updateCountdown()" />
        </p>

        <p>TIME:
            <select id="hour" onChange="updateCountdown()">
%for hour in range(24):
    %selected = ' selected' if now.hour == hour else ''
                <option value="{{hour}}"{{selected}}>{{number_formatter(hour)}}</option>
%end
            </select> :
            <select id="minute" onChange="updateCountdown()">
%for minute in range(60):
    %selected = ' selected' if now.minute == minute else ''
                <option value="{{minute}}"{{selected}}>{{number_formatter(minute)}}</option>
%end
            </select>
        </p>

        <select id="games" onChange="updateCountdown()">
            <option value="null">GAME-INDEPENDENT</option>
        </select>
        <p>URL: <span id="schedule_url"></span></p>
        <p>Discord Time: <span id="discord_prompt"></span>
            <img class="icon" src="/static/copy.png" title="COPY TO CLIPBOARD" onClick="copyDiscordPrompt()" />
        </p>
    </form>
</div>