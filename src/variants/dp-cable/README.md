# Variant: active DisplayPort → HDMI 2.1 cable

*Русский — ниже.*

**Not in use on atrium.** The TV is connected to the box's own HDMI 2.1 (see `docs/en/tv-output.md`). This
folder keeps what we used while the TV was connected through an active DP → HDMI 2.1 cable (Chrontel
CH7218), in case your HDMI port does not carry HDMI 2.1 or your kernel is older than 7.2.

## The problem it solves

When it blanks the screen, the amdgpu driver puts the chip in the cable to sleep (DPCD `0x600 = 02`). After a
long blank the chip sometimes does not bring the HDMI side back: the box sends the picture, the DP link is up,
the TV says "No signal". Unplugging and plugging the cable back fixes it. These files do the same in
software right after the screen wakes up: `trigger_hotplug` in amdgpu debugfs drops and re-detects the link,
and GNOME applies the mode again. The TV blinks once, about 6 seconds after waking up.

The chip's power (3.3 V from the DP port) cannot be switched off from software, so this is the closest
thing to a physical replug. Whether it helps against every stuck state is not proven: it was installed only
for a few hours before we moved to HDMI 2.1.

| File | Goes to | What it does |
|---|---|---|
| `atrium-dp-replug` | `/usr/local/bin/` | waits 3 s, then unplug/plug of every connected DP output; does nothing while an RDP client is connected (mutter 50.5 crashed on a display change during RDP) |
| `atrium-dp-replug.service` | `/etc/systemd/system/` | one-shot service that runs the script as root (debugfs needs root) |
| `50-atrium-dp-replug.rules` | `/etc/polkit-1/rules.d/` | lets the TV user `view` start only this one service |
| `atrium-screensaver-replug.patch` | patch for `/usr/local/bin/atrium-screensaver` | the screensaver starts the service when it turns the monitor back on |

Install (from the repository copy in `/root/atrium`):

```bash
V=/root/atrium/src/variants/dp-cable
install -m 755 $V/atrium-dp-replug /usr/local/bin/atrium-dp-replug
install -m 644 $V/atrium-dp-replug.service /etc/systemd/system/atrium-dp-replug.service
install -m 644 $V/50-atrium-dp-replug.rules /etc/polkit-1/rules.d/50-atrium-dp-replug.rules
\cp -a /usr/local/bin/atrium-screensaver /usr/local/bin/atrium-screensaver.bak-$(date +%Y%m%d)
patch -p1 -d / < $V/atrium-screensaver-replug.patch
restorecon /usr/local/bin/atrium-dp-replug /usr/local/bin/atrium-screensaver /etc/systemd/system/atrium-dp-replug.service /etc/polkit-1/rules.d/50-atrium-dp-replug.rules
systemctl daemon-reload && systemctl --user -M view@ restart atrium-screensaver
```

Test (the TV blinks once): `runuser -u view -- systemctl start atrium-dp-replug.service && journalctl -u atrium-dp-replug -n 3`.

Remove: put the screensaver back from the backup, delete the three files, `systemctl daemon-reload`, restart
the screensaver.

## CEC through the cable

The reflashed CH7218 cable (and the Synaptics VMM7100 adapter) passes HDMI-CEC over the DP service channel:
Linux gets `/dev/cec0` and the TV remote works as an input device. With `v4l-utils` installed:

```bash
cec-ctl -d /dev/cec0 --playback --osd-name atrium   # register atrium on the CEC bus
cec-ctl -d /dev/cec0 -S                             # show the TV and other devices
cec-ctl -d /dev/cec0 --to 0 --standby               # TV to standby
cec-ctl -d /dev/cec0 --to 0 --image-view-on         # TV on
```

We checked: the LG C3 obeys `--standby`, and in standby it does not drop HDMI — the DP output stays
connected and the chip stays awake. Turning the TV off over CEC instead of blanking the output was an option
against the cable getting stuck; we did not finish that test. The box's own HDMI has no CEC in Linux.

---

# Вариант: активный кабель DisplayPort → HDMI 2.1

**На atrium не используется.** ТВ подключён к штатному HDMI 2.1 бокса (см. `docs/ru/tv-output.md`). Здесь
лежит то, чем мы пользовались, пока ТВ был подключён через активный кабель DP → HDMI 2.1 (Chrontel
CH7218), — на случай, если твой порт HDMI не держит HDMI 2.1 или ядро старше 7.2.

## Какую проблему решает

Гася экран, драйвер amdgpu усыпляет чип в кабеле (DPCD `0x600 = 02`). После долгого гашения чип иногда не
поднимает сторону HDMI: бокс отдаёт картинку, линия DP поднята, а ТВ пишет «Нет сигнала». Помогает вынуть и
вставить кабель. Эти файлы делают то же самое программно сразу после пробуждения экрана: `trigger_hotplug` в
debugfs amdgpu разрывает и заново находит линию, GNOME заново выставляет режим. ТВ один раз моргает
примерно через 6 секунд после пробуждения.

Питание чипа (3,3 В от порта DP) программно не выключить, так что это самое близкое к физическому
переподключению. Помогает ли от любого застревания — не доказано: вариант проработал несколько часов, потом
мы перешли на HDMI 2.1.

| Файл | Куда | Что делает |
|---|---|---|
| `atrium-dp-replug` | `/usr/local/bin/` | ждёт 3 с, потом «вынул-вставил» для каждого подключённого DP; при подключённом RDP ничего не делает (mutter 50.5 падал при смене экрана во время RDP) |
| `atrium-dp-replug.service` | `/etc/systemd/system/` | разовая служба, запускает скрипт от root (debugfs только для root) |
| `50-atrium-dp-replug.rules` | `/etc/polkit-1/rules.d/` | разрешает пользователю ТВ `view` запускать только эту службу |
| `atrium-screensaver-replug.patch` | патч к `/usr/local/bin/atrium-screensaver` | заставка запускает службу, когда включает экран |

Установка и удаление — командами из английской части выше. Проверка: ТВ моргнёт один раз.

## CEC через кабель

Прошитый кабель CH7218 (и переходник Synaptics VMM7100) передаёт HDMI-CEC по служебному каналу DP: в Linux
появляется `/dev/cec0`, а пульт ТВ работает как устройство ввода. Команды `cec-ctl` (пакет `v4l-utils`) —
в английской части выше: регистрация atrium, список устройств, сон и включение ТВ.

Проверено: LG C3 слушается `--standby`, и во сне HDMI не отключает — выход DP остаётся подключённым, чип не
засыпает. Выключать ТВ по CEC вместо гашения выхода — один из вариантов против застревания кабеля; этот
тест мы не довели. У штатного HDMI бокса CEC в Linux нет.
