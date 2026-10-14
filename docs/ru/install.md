# Установка atrium с нуля

[English version](../en/install.md) · [Железо и BIOS](hardware.md) · [Обновления](updates.md) · [Известные проблемы](problems.md) · [Вывод на ТВ](tv-output.md) · [Стрим игр](streaming.md)

Эта инструкция повторяет atrium по шагам: от голого бокса до медиацентра у ТВ. У каждого шага сказано,
что делаем и зачем. Команды взяты из истории настоящей установки и проверены на живом боксе.

**Как читать команды.** Всё в блоках `bash` выполняется на боксе от `root` по SSH, если не
сказано иначе. Блоки `powershell` выполняются на компьютере с Windows. Каждый блок можно вставлять
целиком: нужные переменные объявлены в его начале.

**Свои значения.** В командах и файлах — примеры: домашняя сеть `192.168.0.0/24`, бокс получает адрес `192.168.0.42` по
статической аренде DHCP на роутере, имя в сети `atrium.lan`, имя машины `atrium.example.com`. Если у тебя
другие, поменяй их в командах ниже и в файлах репозитория. Где они встречаются, показывает команда
`grep -rn "192\.168\.0\.\|atrium\.lan\|example\.com" rootfs src`.

---

## 0. Что понадобится

- Бокс **Beelink SER5 MAX** (Ryzen 7 7735U, Radeon 680M) и второй NVMe на 2 ТБ под медиа. Полный
  список, настройки BIOS и всё про ТВ — в [hardware.md](hardware.md).
- Пассивный кабель **HDMI Ultra High Speed (48G)** от HDMI бокса к ТВ. С параметром ядра из шага 12
  штатный HDMI даёт 4K 120 Гц, RGB, 10 бит и HDR (подробно в [tv-output.md](tv-output.md)).
- USB-ЦАП, если нужен хороший звук (у нас SMSL). Встроенный звук бокса мы выключаем.
- Флешка от 2 ГБ, USB-клавиатура (для BIOS и установщика) и проводная сеть с DHCP.
- Второй компьютер для SSH. BIOS обновляется из Windows самого бокса, до его стирания.

## 1. BIOS — до установки

**Зачем.** Свежий BIOS снимает ограничение мощности видеоядра, а настройки ниже отключают всё, что
мешает медиацентру: сон, энергосбережение линий PCIe, HDMI-звук, сетевую загрузку.

1. **Обновление BIOS до ASER5012** делается из Windows, которая стоит на боксе с завода, до установки
   Linux. Как именно, с какими флагами и почему так — в [hardware.md](hardware.md), раздел «BIOS».
2. **Настройки.** Клавиша **Del** при включении открывает BIOS, **F7** — меню загрузки. Полная таблица
   настроек с объяснениями — в [hardware.md](hardware.md), раздел «Настройки BIOS». Главное:
   - сон и гибернация в ACPI — выключить (бокс работает как сервер, сна нет никогда);
   - ASPM на всех портах PCIe — Disabled (линии не засыпают, нет подвисаний и задержек);
   - NB Azalia (HDMI-звук) — Disabled, звук идёт только через USB-ЦАП;
   - UMA Frame Buffer — **4G** (эмуляторам до PS3 нужна видеопамять);
   - AC Power Loss — Always On (после отключения света бокс включится сам);
   - Network Stack и PXE — Disabled, Quiet Boot — Disabled.

## 2. Кабель к ТВ

Обычный пассивный кабель HDMI **Ultra High Speed (48G)** из HDMI бокса в любой вход HDMI 2.1 телевизора.
Ничего прошивать не надо. В паспорте порт бокса записан как HDMI 2.0, но HDMI 2.1 он держит: его
включает параметр ядра `amdgpu.dcfeaturemask=0x402` на шаге 12. До этого шага картинка будет в HDMI 2.0
(4K 60 Гц), так и должно быть.

Как мы месяц мучились с активными кабелями DP → HDMI 2.1, прежде чем это нашли, и запасной путь, если
твой порт HDMI 2.1 не держит, — [tv-output.md](tv-output.md).

## 3. Установка Fedora

**Зачем именно так.** Сетевой установщик Fedora Everything ставит голую систему, без набора программ
Workstation. Дальше мы ставим ровно то, что нужно медиацентру, и знаем каждый пакет.

1. Скачай **Fedora Everything, Network Install, x86_64** — https://fedoraproject.org/misc/ (раздел Everything)
   (у нас Fedora 44). Запиши флешку программой Fedora Media Writer или `dd`.
2. Загрузись с флешки (F7 → флешка) и пройди установщик:
   - **Language:** English (United States). Русский интерфейс GNOME не нужен, а в консоли английский
     надёжнее.
   - **Keyboard:** English (US).
   - **Time & Date:** регион Etc / UTC — системные часы в UTC, местное время пользователь ТВ получает
     отдельно (шаг 9). В **NTP servers** мы указали домашний роутер (`router.lan`); можно оставить пул
     Fedora по умолчанию.
   - **Software Selection:** **Fedora Custom Operating System**, без дополнений. Это самая голая база.
   - **Installation Destination:** выбери **только системный диск** (у нас Crucial P3 Plus 1 ТБ), второй
     диск не трогай. **Custom**, разделы вручную:

     | Точка монтирования | Размер | Файловая система | Зачем |
     |---|---|---|---|
     | `/boot/efi` | 600 MiB | EFI System Partition | загрузчик UEFI |
     | `/boot` | 2 GiB | ext4 | ядра; 2 ГБ хватает на три ядра с запасом |
     | `/` | всё остальное | ext4 | система и программы |

     Раздела подкачки нет: Fedora сама включает подкачку в памяти (zram).
   - **Root Account:** включи root, задай пароль и поставь галку **Allow root SSH login with password**.
     Пользователя здесь не создавай: пользователь ТВ `view` появится на шаге 6 и должен получить uid 1000 —
     на этот номер завязаны команды ниже (`/run/user/1000`).
3. **Begin Installation**, по окончании — **Reboot System**, флешку вынь.

## 4. Первый вход по SSH и получение репозитория

**Зачем.** Дальше всё делается с основного компьютера по SSH. Вход по ключу избавляет от пароля и
позволяет вставлять длинные команды.

На ПК с Windows создай ключ и отправь его на бокс. Адрес бокса посмотри в аренде DHCP на роутере или
командой `ip a` на самом боксе.

```powershell
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\atrium_ed25519" -N '""' -C "atrium"
scp "$env:USERPROFILE\.ssh\atrium_ed25519.pub" root@192.168.0.42:/tmp/
```

На боксе (последний раз по паролю: `ssh root@192.168.0.42`):

```bash
install -d -m 700 /root/.ssh && tr -d '\r' < /tmp/atrium_ed25519.pub >> /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys && restorecon -R /root/.ssh && rm -f /tmp/atrium_ed25519.pub
```

Дальше входи так: `ssh -i ~/.ssh/atrium_ed25519 root@192.168.0.42`.

Теперь положи этот репозиторий на бокс в `/root/atrium`. Если у тебя есть доступ к нему на GitHub:

```bash
dnf -y install git && git clone https://github.com/sidex100/atrium.git /root/atrium
```

Если репозиторий закрытый и доступа с бокса нет, скачай его на ПК (Code → Download ZIP), распакуй и
скопируй папку: `scp -r atrium root@192.168.0.42:/root/`.

## 5. База: имя, обновления, RPM Fusion, видео через видеокарту

**Зачем.** RPM Fusion даёт то, чего нет в Fedora из-за патентов: полный ffmpeg и драйвер аппаратного
декодирования H.264/HEVC для видеокарт AMD (`mesa-va-drivers-freeworld`). Без него видео декодирует
процессор. `fastestmirror` и параллельные загрузки нужны потому, что ближние зеркала у нас часто висли.

```bash
R=/root/atrium/rootfs
hostnamectl set-hostname atrium.example.com
\cp -a /etc/dnf/dnf.conf /etc/dnf/dnf.conf.bak-$(date +%Y%m%d) && install -m 644 $R/etc/dnf/dnf.conf /etc/dnf/dnf.conf
dnf -y upgrade --refresh
dnf -y install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm pciutils usbutils
for k in /etc/pki/rpm-gpg/RPM-GPG-KEY-rpmfusion-*-fedora-$(rpm -E %fedora); do echo "$k"; gpg --show-keys --with-fingerprint "$k" 2>/dev/null | grep -A1 '^pub'; done
```

Сверь отпечатки ключей с https://rpmfusion.org/keys. Потом драйвер видео и проверка:

```bash
dnf -y install mesa-va-drivers-freeworld ffmpeg libva-utils
vainfo --display drm 2>&1 | grep -E "Driver version|VAProfile(H264|HEVC|VP9|AV1)"
```

В выводе должны быть профили H.264, HEVC (в том числе Main10), VP9 и AV1.

24-часовое время в консоли, как на наших серверах:

```bash
R=/root/atrium/rootfs
\cp -a /etc/locale.conf /etc/locale.conf.bak-$(date +%Y%m%d) && install -m 644 $R/etc/locale.conf /etc/locale.conf
```

## 6. GNOME, пользователь ТВ, автовход, никакого сна

**Зачем.** Ставим только оболочку GNOME (Wayland) и то, без чего она неполноценна. Пользователь `view` —
это ТВ: без пароля, входит сам. Сон отключён на уровне systemd: бокс работает круглые сутки (торренты,
общая папка, удалённый доступ).

```bash
dnf -y install mc nano htop gnome-shell gdm gnome-session-wayland-session gnome-control-center nautilus ptyxis gnome-shell-extension-dash-to-dock xdg-desktop-portal-gnome xdg-user-dirs-gtk gnome-keyring pipewire-alsa
dnf mark user tuned
dnf remove --assumeno gnome-tour malcontent-control tuned-ppd
```

Последняя команда только показывает, что будет удалено. **Любое `dnf remove` сначала смотри с
`--assumeno`**: dnf удаляет и «осиротевшие» зависимости. Так однажды вместе с ненужным пакетом ушёл
файловый менеджер. Строка `dnf mark user tuned` защищает `tuned` от такого удаления. Если в списке только
эти три пакета, удаляй:

- `gnome-tour` — приветственный тур;
- `malcontent-control` — родительский контроль;
- `tuned-ppd` — переключатель режимов питания в меню; режим у нас всегда «производительность».

```bash
R=/root/atrium/rootfs
dnf -y remove gnome-tour malcontent-control tuned-ppd
systemctl --global mask localsearch-3.service
systemctl enable --now tuned && tuned-adm profile throughput-performance
useradd -c TV view && passwd -d view && id view
\cp -a /etc/gdm/custom.conf /etc/gdm/custom.conf.bak-$(date +%Y%m%d) && install -m 644 $R/etc/gdm/custom.conf /etc/gdm/custom.conf
systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target
systemctl set-default graphical.target
```

- `localsearch` — индексатор файлов GNOME. Медиацентру он не нужен и грузит диск.
- `throughput-performance` — процессор всегда на высоких частотах, без задержек на разгон. Turbo и
  C-состояния при этом работают, в простое бокс тратит 3–4 Вт.
- `custom.conf` — автовход `view` и **повторный вход через 5 секунд**, если сеанс GNOME упал. Сеанс
  однажды упал от бага mutter (см. [problems.md](problems.md)), и RDP вернулся сам.

Пока не перезагружай: сначала диск под медиа.

## 7. Второй диск: /srv

**Зачем.** Фильмы, музыка, загрузки и игры живут на отдельном NVMe 2 ТБ, смонтированном в `/srv`. Система
не зависит от него: при сбое диска (`nofail`) бокс всё равно загрузится.

Если диск — WD Blue SN5000, сначала обнови его прошивку (291020WD → 291050WD). Как — в
[hardware.md](hardware.md), раздел «Прошивка WD Blue SN5000». Затем размечаем. Команда ищет диск
**по модели**, а не по имени `nvme0`/`nvme1`: имена меняются от загрузки к загрузке. Она остановится, если
на диске уже есть разделы.

```bash
M="WD Blue SN5000 2TB"
D=$(for c in /sys/class/nvme/nvme*; do [ "$(xargs < $c/model)" = "$M" ] && echo /dev/${c##*/}n1; done); echo "disk = $D"
[ -b "$D" ] && [ "$(lsblk -n -o NAME $D | wc -l)" = 1 ] && parted -s $D mklabel gpt mkpart srv xfs 1MiB 100% && udevadm settle && mkfs.xfs -L srv ${D}p1 && U=$(blkid -p -s UUID -o value ${D}p1) && \cp -p /etc/fstab /etc/fstab.bak-$(date +%Y%m%d) && printf '%s\n' "# /srv on the media NVMe; nofail - boot even without it" "UUID=$U /srv xfs defaults,nofail 0 0" >> /etc/fstab && systemctl daemon-reload && mkdir -p /srv && mount /srv && findmnt /srv
```

Папки. `2775` и группа `view` нужны, чтобы в них могли писать и ТВ, и Transmission, и общая папка Samba:

```bash
install -d -o view -g view -m 2775 /srv/video /srv/music /srv/download /srv/torrent /srv/docs /srv/pics /srv/games
restorecon -R /srv && ls -l /srv
reboot
```

После перезагрузки на ТВ откроется рабочий стол GNOME пользователя `view`.

## 8. Программы

**Зачем каждая.**

- **Браузеры.** Google Chrome — основной: свои кодеки, Widevine, самый быстрый. Firefox — запасной, с
  системным ffmpeg и VA-API. Chromium — для тестов.
- **Плееры.** **mpv** — плеер по умолчанию для всех видео, лучшее качество. MPC-QT — оболочка mpv в стиле
  MPC-HC. VLC — на всякий случай. **fooyin** — музыка в стиле foobar2000.
- **Торренты.** Transmission Remote GTK — окно для демона торрентов (шаг 13).
- **Внешний вид.** Шрифты Geist и Inter, тёмная тема GTK3, эмодзи. Freon — температура процессора в
  панели. Just Perfection — убирает лишнее из меню GNOME.
- **Spotify** — из Flathub.

```bash
dnf -y group install standard
dnf -y install fedora-workstation-repositories && dnf config-manager setopt google-chrome.enabled=1
dnf -y install google-chrome-stable firefox chromium mpv mpc-qt vlc vlc-plugins-freeworld fooyin transmission-remote-gtk flatpak gnome-tweaks gnome-backgrounds adw-gtk3-theme google-noto-color-emoji-fonts rsms-inter-vf-fonts vercel-geist-fonts vercel-geist-mono-fonts gnome-shell-extension-freon gnome-shell-extension-just-perfection lm_sensors
rpm -qa 'gpg-pubkey*' --qf '%{version} %{summary}\n' | grep -i google
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install -y --noninteractive flathub com.spotify.Client
```

Ключ Google должен иметь отпечаток `EB4C 1BFD 4F04 2F6D DDCC EC91 7721 F63B D38B 4796`. Проверить его
можно командой `rpm -qi gpg-pubkey-d38b4796`.

## 9. Настройки: система и пользователь ТВ

**Зачем.**

- **Firefox** — политика убирает домашнюю страницу и плитки Fedora.
- **Chromium** — `master_preferences` убирает стартовую страницу Fedora. Это касается только нового
  профиля.
- **Тёмная тема** закреплена замком dconf: светлую из меню не выбрать.
- **Значки дока** закреплены замком dconf: их нельзя открепить или переставить мышью. Менять — правкой
  файла и `dconf update`.
- **atrium-no-overview** — GNOME 50 открывает обзор (поиск и рабочие столы) сразу при входе, а расширения
  загружаются слишком поздно, чтобы это остановить. Скрипт закрывает обзор через D-Bus.
- **Обои** — картина Гюстава Буланже (1861, общественное достояние) с подписью ATRIUM. Вечерний вариант:
  тёплый свет в центре, тёмные края. Генератор лежит в `src/wallpaper/`.
- **Файлы пользователя `view`.** Ассоциации (видео → mpv, явный звук → fooyin, ссылки → Chrome), настройки
  mpv, MPC-QT и VLC, часовой пояс ТВ (в репозитории пример `TZ=UTC` — поставь свой), папки «Видео/Музыка/Загрузки/Документы/Изображения» в `/srv`,
  закладки файлового менеджера, режим экрана (`monitors.xml`: 3840×2160, 120 Гц, масштаб 250 %, SDR).
- **Авто-HDR.** Рабочий стол работает в SDR: в HDR GNOME пересобирает каждый кадр, и видеокарте не
  хватает запаса на 4K HDR в браузере. HDR включается сам, только пока mpv играет HDR-видео (PQ или HLG):
  скрипт `auto-hdr.lua` в настройках mpv ставит паузу, вызывает `atrium-hdr on` и через 2 секунды
  продолжает; когда видео кончилось или mpv закрыт — `atrium-hdr off`. ТВ при каждом переключении моргает
  на 1–2 секунды. Пока подключён RDP, `atrium-hdr` экран не переключает (GNOME 50 падал при смене экрана
  во время RDP). Вручную: `atrium-hdr on|off|status` от пользователя `view`.

```bash
R=/root/atrium/rootfs
install -D -m 644 $R/etc/firefox/policies/policies.json /etc/firefox/policies/policies.json
\cp -a /etc/chromium/master_preferences /etc/chromium/master_preferences.bak-$(date +%Y%m%d) && install -m 644 $R/etc/chromium/master_preferences /etc/chromium/master_preferences
install -D -m 644 -t /etc/dconf/db/local.d $R/etc/dconf/db/local.d/00-atrium-dark $R/etc/dconf/db/local.d/00-atrium-dock
install -D -m 644 -t /etc/dconf/db/local.d/locks $R/etc/dconf/db/local.d/locks/00-atrium-dark $R/etc/dconf/db/local.d/locks/00-atrium-dock
dconf update
install -m 755 $R/usr/local/bin/atrium-no-overview /usr/local/bin/atrium-no-overview
install -m 755 $R/usr/local/bin/atrium-hdr /usr/local/bin/atrium-hdr
install -D -m 644 -t /usr/local/share/backgrounds/atrium $R/usr/local/share/backgrounds/atrium/atrium-painting-evening-v2-4k.png
cp -r --no-preserve=ownership $R/home/view/.config/. /home/view/.config/ && chown -R view:view /home/view/.config && chmod 600 /home/view/.config/vlc/vlcrc
restorecon -R /etc/firefox /etc/chromium /etc/dconf /usr/local /home/view
```

Настройки GNOME пользователя `view` (тема, шрифты, раскладки, панель, расширения) загружаются в его
работающий сеанс. Что означает каждая строка — в комментариях в начале файла
`src/dconf/view-atrium.ini`.

```bash
V="runuser -u view -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
$V dconf load / < /root/atrium/src/dconf/view-atrium.ini
$V gsettings get org.gnome.desktop.interface clock-format
```

Раскладки получаются такие: Alt+Shift переключает, Caps Lock включает английскую, Shift+Caps — русскую,
правый Alt работает как AltGr.

## 10. Расширения GNOME и загрузка в панели

**Зачем.** В панели GNOME видно, кто сейчас работает (CPU, GPU, VIDEO — аппаратный декодер видео),
скорость сети и температура. На рабочем столе — заполнение дисков. Клики по этим гаджетам ничего не
открывают. Наши расширения:

| Расширение | Что делает |
|---|---|
| `atrium-lock` | запрещает клики и меню у Freon и виджетов рабочего стола (Executor закрыт своей настройкой) |
| `atrium-brightness-value` | показывает точное значение HDR-яркости рядом с ползунком и на полоске внизу |
| `atrium-no-dnd-icon` | прячет колокольчик «Не беспокоить»: уведомлений на ТВ нет вообще |

Все расширения ставим **системными** в `/usr/local/share/gnome-shell/extensions`. Причина: настройка
`allow-extension-installation false` (GNOME не проверяет обновления и не показывает уведомлений) в
GNOME 50 перестаёт загружать расширения из домашней папки.

Три чужих расширения скачиваем с extensions.gnome.org ровно тех версий, что стоят на atrium, и сверяем
контрольные суммы:

| Расширение | Версия | Что даёт |
|---|---|---|
| Executor | 30 | вывод команды в панели: загрузка CPU/GPU/VIDEO и скорость сети |
| Desktop Widgets (azclock) | 21 (16.1) | текст на рабочем столе: `df` и `du` дисков |
| GJS OSK | 53 | экранная клавиатура как в Windows |

```bash
E=/usr/local/share/gnome-shell/extensions; mkdir -p $E; cd /tmp
while read -r uuid tag sum; do
  curl -fsSL -o ext.zip "https://extensions.gnome.org/download-extension/$uuid.shell-extension.zip?version_tag=$tag" &&
  echo "$sum  ext.zip" | sha256sum -c - && rm -rf "$E/$uuid" && mkdir "$E/$uuid" && unzip -q ext.zip -d "$E/$uuid" &&
  { [ -f "$E/$uuid/schemas/gschemas.compiled" ] || glib-compile-schemas "$E/$uuid/schemas"; } && rm -f ext.zip
done <<'EOF'
executor@raujonas.github.io 70219 1ea446f27f7d33cf58b14fc440f33ac6ec50ae9c50c5e3dec53594a4939ddb07
azclock@azclock.gitlab.com 75151 79b0e9fcd4d11fb86985dd64eef4d4f6310698a6c37646507812bc3e2eb5b603
gjsosk@vishram1123.com 74269 38578bfb54880c8fec13e24783406d4c77ad047b5bc205b7a5814dc631231b6d
EOF
R=/root/atrium/rootfs
cp -r $R/usr/local/share/gnome-shell/extensions/. $E/
chown -R root:root $E && chmod -R u=rwX,go=rX $E && restorecon -R $E && ls $E
```

Служба `atrium-sysload` раз в секунду пишет загрузку CPU/GPU/VIDEO и скорость сети в `/run/atrium-sysload/`,
а Executor показывает эти строки в панели. Служба работает от одноразового пользователя без прав, без
сети и с системой только на чтение. Данные берёт из счётчиков ядра: `gpu_busy_percent`, `vcn_busy_percent`
(декодер видео), `/proc/stat` и счётчиков сетевых адаптеров.

Служба запускает `/usr/local/sbin/atrium-sysload`, а файл кладём в `/usr/local/bin` — это одно и то же:
в Fedora 42 и новее `/usr/local/sbin` — ссылка на `bin` (её создаёт пакет `filesystem`).

```bash
R=/root/atrium/rootfs
install -m 755 $R/usr/local/bin/atrium-sysload /usr/local/bin/atrium-sysload
install -m 644 $R/etc/systemd/system/atrium-sysload.service /etc/systemd/system/atrium-sysload.service
restorecon /usr/local/bin/atrium-sysload /etc/systemd/system/atrium-sysload.service
systemctl daemon-reload && systemctl enable --now atrium-sysload && sleep 2 && cat /run/atrium-sysload/panel /run/atrium-sysload/net
reboot
```

GNOME видит новые системные расширения только после нового входа, поэтому перезагружаемся. Проверка
после перезагрузки:

```bash
V="runuser -u view -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
$V gnome-extensions list --enabled --details | grep -E "^[a-z]|State"
```

У всех должно быть `State: ACTIVE`.

## 11. Заставка Apple Aerial и выключение экрана

**Зачем.** У GNOME нет заставки, он умеет только гасить экран. А гашение средствами GNOME поднимает «щит»
экрана, под которым GNOME запрещает удалённый рабочий стол (RDP молча не подключается). Поэтому:

- **15 минут без ввода** — на весь экран идут ролики Apple Aerial (города, природа, МКС, под водой) в 4K,
  без звука;
- **30 минут** — экран выключается через Mutter (тот же выключатель, которым пользуется сам GNOME), но без
  щита;
- **любое касание** мыши, клавиатуры, пульта или RDP — всё возвращается;
- пока идёт фильм или YouTube, плеер держит запрет простоя, и заставка не мешает.

Ролики — собственность Apple, в репозитории их нет: скачиваем с серверов Apple. Это 20 роликов, 7,9 ГБ.
Сервер Apple подписан корневым сертификатом Apple, которому Fedora не доверяет, поэтому закачка идёт с этим
корнем явно. В системное доверие он не добавляется.

```bash
d=/usr/local/share/atrium-screensaver && u=https://sylvan.apple.com/Aerials/2x/Videos && install -d -m 755 $d/aerial && curl -sSf https://www.apple.com/appleca/AppleIncRootCertificate.cer | base64 -w64 | sed -e '1i -----BEGIN CERTIFICATE-----' -e '$a -----END CERTIFICATE-----' > $d/apple-root.pem && systemd-run --unit=atrium-aerial-fetch curl -sSf --retry 3 --cacert $d/apple-root.pem --output-dir $d/aerial -o new-york.mov $u/comp_N008_C009_PS_v01_SDR_PS_20180925_SDR_4K_HEVC.mov -o hong-kong.mov $u/comp_HK_H004_C008_PSNK_v19_SDR_PS_20180914_SDR_4K_HEVC.mov -o dubai.mov $u/comp_DB_D008_C010_PSNK_v21_SDR_PS_20180914_F0F16157_SDR_4K_HEVC.mov -o london.mov $u/comp_L007_C007_PS_v01_SDR_PS_20180925_SDR_4K_HEVC.mov -o san-francisco.mov $u/comp_A012_C014_1223PT_v53_SDR_PS_FINAL_20180709_F0F8700_SDR_4K_HEVC.mov -o iceland.mov $u/I003_C008_SDR_4K_HEVC.mov -o greenland.mov $u/comp_GL_G002_C002_PSNK_v03_SDR_PS_20180925_SDR_4K_HEVC.mov -o yosemite.mov $u/Y005_C003_SDR_4K_HEVC.mov -o patagonia.mov $u/P006_C002_UHD_SDR_4K_HEVC.mov -o hawaii.mov $u/comp_H005_C012_PS_v01_SDR_PS_20180925_SDR_4K_HEVC.mov -o scotland.mov $u/S006_C007_SDR_4K_HEVC.mov -o grand-canyon.mov $u/G010_C026_UHD_SDR_v02_4K_HEVC.mov -o space-north-america-aurora.mov $u/comp_GMT314_139M_170NC_NORTH_AMERICA_AURORA__COMP_v22_SDR_20181206_v12CC_SDR_4K_HEVC.mov -o space-new-york-night.mov $u/comp_GMT307_136NC_134K_8277_NY_NIGHT_01_v25_SDR_PS_20180907_SDR_4K_HEVC.mov -o space-africa-night.mov $u/comp_GMT312_162NC_139M_1041_AFRICA_NIGHT_v14_SDR_FINAL_20180706_SDR_4K_HEVC.mov -o space-caribbean-day.mov $u/comp_GMT308_139K_142NC_CARIBBEAN_DAY_v09_SDR_FINAL_22062018_SDR_4K_HEVC.mov -o sea-california-kelp.mov $u/g201_CA_A016_C002_SDR_20191114_SDR_4K_HEVC.mov -o sea-humpback-whale.mov $u/g201_WH_D004_L014_SDR_20191031_SDR_4K_HEVC.mov -o sea-palau-jellies.mov $u/PA_A010_C007_SDR_20190717_SDR_4K_HEVC.mov -o sea-california-dolphins.mov $u/DL_B002_C011_SDR_20191122_SDR_4K_HEVC.mov
```

Закачка идёт фоном, минут 5–10. Следить: `systemctl status atrium-aerial-fetch`, `du -sh $d/aerial`.
Другие ролики: каталог Apple лежит в `https://sylvan.apple.com/Aerials/resources-16.tar`
(`entries.json`, 114 роликов), имена файлов `*_SDR_4K_HEVC.mov`.

Сама заставка — служба в сеансе пользователя ТВ:

```bash
R=/root/atrium/rootfs
install -m 755 $R/usr/local/bin/atrium-screensaver /usr/local/bin/atrium-screensaver
install -m 644 $R/etc/systemd/user/atrium-screensaver.service /etc/systemd/user/atrium-screensaver.service
restorecon /usr/local/bin/atrium-screensaver /etc/systemd/user/atrium-screensaver.service
systemctl --global enable atrium-screensaver.service
systemctl --user -M view@ daemon-reload && systemctl --user -M view@ start atrium-screensaver.service && systemctl --user -M view@ is-active atrium-screensaver.service
```

## 12. Звук и параметры ядра (в том числе HDMI 2.1)

**Зачем.** Встроенный аналоговый звук бокса (`1022:15e3`) в BIOS не выключается. Мы прячем его от системы
параметром ядра `pci-stub`, и единственной звуковой картой остаётся USB-ЦАП: никакого выбора выхода, всё
идёт в ЦАП. PipeWire работает на 48 кГц, но когда играет один поток, ЦАП переключается на частоту трека
(44,1–192 кГц), то есть без пересчёта.

Параметры ядра, всё сразу:

- `pci-stub.ids=1022:15e3` — прячет встроенный звук;
- `amdgpu.dcfeaturemask=0x402` — включает HDMI 2.1 (FRL) на штатном HDMI: 4K 120 Гц, RGB, 10 бит, HDR.
  В ядре 7.2 он выключен по умолчанию. `0x2` — значение по умолчанию, `0x400` — бит FRL
  ([tv-output.md](tv-output.md));
- `efi_pstore.pstore_disable=0` и `amdgpu.ppfeaturemask=0xfff73fff` — часть ловушки на зависания,
  объяснены на шаге 16.

`grubby --update-kernel=ALL` в Fedora сам дописывает параметры и в `/etc/default/grub`, а иногда и в
`/etc/kernel/cmdline`, поэтому в `/etc/kernel/cmdline` добавляем только то, чего там ещё нет. Если
`/etc/kernel/cmdline` нет, новые ядра возьмут параметры из текущей загрузки — пропускаем.

```bash
A="pci-stub.ids=1022:15e3 efi_pstore.pstore_disable=0 amdgpu.ppfeaturemask=0xfff73fff amdgpu.dcfeaturemask=0x402"
R=/root/atrium/rootfs
for f in /etc/kernel/cmdline /etc/default/grub; do [ ! -f $f ] || \cp -p $f $f.bak-$(date +%Y%m%d); done
grubby --update-kernel=ALL --args="$A"
[ ! -f /etc/kernel/cmdline ] || for p in $A; do grep -q -- "$p" /etc/kernel/cmdline || sed -i "1s|\$| $p|" /etc/kernel/cmdline; done
install -m 644 $R/etc/default/grub /etc/default/grub
install -D -m 644 $R/etc/pipewire/pipewire.conf.d/50-atrium-rates.conf /etc/pipewire/pipewire.conf.d/50-atrium-rates.conf
grubby --info=ALL | grep -E "^args"; cat /etc/kernel/cmdline 2>/dev/null
```

Изменения затронут три места:

- `grubby` — уже установленные ядра;
- `/etc/kernel/cmdline` — ядра, которые поставятся при обновлениях;
- `/etc/default/grub` — пересборку меню загрузки.

Подействует после перезагрузки (шаг 18). Тогда `aplay -l` покажет только ЦАП.

## 13. Торренты и общая папка

**Transmission.** Демон работает всегда как служба и сам качает в `/srv/download`. Файл `.torrent`,
брошенный в `/srv/torrent` (в том числе с Windows через общую папку), сразу встаёт в закачку. Настройки
«без палева»:

- шифрование обязательно;
- DHT, LPD и uTP выключены — они выдают закачку в сети;
- раздача останавливается сразу после закачки;
- веб-интерфейс и удалённое управление открыты только в домашней сети.

На ТВ им управляет Transmission Remote GTK.

```bash
R=/root/atrium/rootfs; L=192.168.0.0/24
dnf -y install transmission-daemon && usermod -aG view transmission
install -d -o transmission -g transmission -m 700 /var/lib/transmission/.config /var/lib/transmission/.config/transmission-daemon
install -o transmission -g transmission -m 600 $R/var/lib/transmission/.config/transmission-daemon/settings.json /var/lib/transmission/.config/transmission-daemon/settings.json
install -D -m 644 $R/etc/systemd/system/transmission-daemon.service.d/override.conf /etc/systemd/system/transmission-daemon.service.d/override.conf
restorecon -R /var/lib/transmission /etc/systemd/system/transmission-daemon.service.d
systemctl daemon-reload && systemctl enable --now transmission-daemon
firewall-cmd --add-service=transmission-client && firewall-cmd --permanent --add-service=transmission-client
r="rule family=\"ipv4\" source address=\"$L\" port port=\"9091\" protocol=\"tcp\" accept"; firewall-cmd --add-rich-rule="$r" && firewall-cmd --permanent --add-rich-rule="$r"
```

`settings.json` правят только при остановленной службе: при остановке демон записывает поверх свои
настройки. В Transmission Remote GTK: Edit → Local Preferences → Connection → `localhost:9091`, путь
`/transmission/rpc`, без логина, галка «подключаться при запуске».

**Samba.** Общая папка `\\atrium.lan\media` — это весь `/srv`, **без логина и пароля** и только для
домашней сети. В корне `/srv` папки не удалить и не переименовать, внутри них читать и писать можно. wsdd
делает atrium видимым в «Сети» Windows.

```bash
R=/root/atrium/rootfs; L=192.168.0.0/24
dnf -y install samba wsdd policycoreutils-python-utils
\cp -a /etc/samba/smb.conf /etc/samba/smb.conf.bak-$(date +%Y%m%d) && install -m 644 $R/etc/samba/smb.conf /etc/samba/smb.conf
\cp -a /etc/sysconfig/wsdd /etc/sysconfig/wsdd.bak-$(date +%Y%m%d) && install -m 644 $R/etc/sysconfig/wsdd /etc/sysconfig/wsdd
semanage fcontext -a -t samba_share_t '/srv(/.*)?' && semanage fcontext -a -t samba_share_t '/srv' && restorecon -R /srv
testparm -s 2>/dev/null | grep -A3 '^\[media\]'
systemctl enable --now smb wsdd
for s in samba wsdd wsdd-http; do r="rule family=\"ipv4\" source address=\"$L\" service name=\"$s\" accept"; firewall-cmd --add-rich-rule="$r" && firewall-cmd --permanent --add-rich-rule="$r"; done
```

Windows 11 по умолчанию не пускает в общие папки без пароля. Один раз на каждом ПК, в PowerShell от
администратора:

```powershell
Set-SmbClientConfiguration -EnableInsecureGuestLogons $true -RequireSecuritySignature $false -Force
```

`/etc/sysconfig/wsdd` содержит имя сетевого интерфейса (`eno1`) и рабочую группу Windows (`WORKGROUP`,
она же в `smb.conf`) — проверь свои: интерфейс — `ip -br link`, группу — на ПК в PowerShell
`(Get-CimInstance Win32_ComputerSystem).Workgroup`. `WORKGROUP` — значение Windows по умолчанию.

**Wi-Fi важнее провода** (по желанию). Если подключить любой Wi-Fi, интернет пойдёт через него, пока он
подключён. Домашняя сеть всегда остаётся на проводе:

```bash
R=/root/atrium/rootfs
\cp -p /etc/NetworkManager/NetworkManager.conf /etc/NetworkManager/NetworkManager.conf.bak-$(date +%Y%m%d) && install -m 644 $R/etc/NetworkManager/NetworkManager.conf /etc/NetworkManager/NetworkManager.conf && nmcli general reload conf
```

## 14. Управление: телефон и RDP

**Unified Remote** превращает телефон в тачпад, клавиатуру и пульт. Сервер официальный, но на Wayland
он работает через `/dev/uinput`, и в нём два недостатка, которые мы правим патчем:

- **короткий тап не кликал.** Сервер шлёт «нажал» и «отпустил» в одном кадре, а GNOME такой клик теряет.
  Патч разделяет их паузой в 15 мс.
- **заглавные буквы, кириллица и символы не печатались.** Сервер знает только простые клавиши. Патч
  печатает каждый символ своей клавишей с нужным модификатором и сам выбирает раскладку (us или ru) под
  символ. Работает при любой раскладке на ТВ.

```bash
mkdir -p /root/dist && cd /root/dist && curl -fL -A "Mozilla/5.0" -o urserver-3.14.0.2574.rpm https://www.unifiedremote.com/static/builds/server/linux-x64/2574/urserver-3.14.0.2574.rpm && echo "8fd30d91781711a4d6a4926c442a8907e46dd80ff0c376667b1efa15c01842ba  urserver-3.14.0.2574.rpm" | sha256sum -c && dnf -y install ./urserver-3.14.0.2574.rpm
cd /opt/urserver/remotes/Unified && patch -p1 --backup --suffix=.orig < /root/atrium/patches/urserver/atrium-urserver.patch
R=/root/atrium/rootfs; L=192.168.0.0/24
install -m 644 $R/etc/udev/rules.d/60-atrium-uinput.rules /etc/udev/rules.d/60-atrium-uinput.rules && udevadm control --reload && modprobe uinput
for p in 9511/udp 9512/tcp 9512/udp; do r="rule family=\"ipv4\" source address=\"$L\" port port=\"${p%/*}\" protocol=\"${p#*/}\" accept"; firewall-cmd --add-rich-rule="$r" && firewall-cmd --permanent --add-rich-rule="$r"; done
runuser -u view -- env HOME=/home/view XDG_SESSION_TYPE=wayland XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus /opt/urserver/urserver-start --no-manager --no-notify
```

- Правило udev даёт пользователю у экрана право создавать виртуальную мышь и клавиатуру (так же делает
  пакет `steam-devices`).
- Первый запуск `urserver-start` сам добавляет сервер в автозапуск `view`.
- В приложении на телефоне сервер находится сам.
- Если у Unified Remote вышла новая версия, контрольная сумма не совпадёт. Тогда возьми новую, а `patch`
  покажет, легли ли правки (подробно в [updates.md](updates.md)).

**RDP** показывает экран ТВ на компьютере: тот же сеанс, тот же рабочий стол. У него свой логин и пароль,
а автовход на ТВ остаётся без пароля. Сертификат самоподписанный, на 10 лет.

```bash
H=atrium.lan; IP=192.168.0.42; L=192.168.0.0/24
dnf -y install openssl
( set -e; D=/home/view/.local/share/gnome-remote-desktop/certificates; G="runuser -u view -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus grdctl rdp"; runuser -u view -- mkdir -p -m 700 $D; runuser -u view -- openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -noenc -subj "/CN=$H" -addext "subjectAltName=DNS:$H,DNS:$(hostname),IP:$IP" -keyout $D/rdp-tls.key -out $D/rdp-tls.crt; chmod 600 $D/rdp-tls.key; $G set-tls-cert $D/rdp-tls.crt; $G set-tls-key $D/rdp-tls.key; $G disable-view-only; $G set-credentials; $G enable )
systemctl --user -M view@ enable --now gnome-remote-desktop.service
r="rule family=\"ipv4\" source address=\"$L\" service name=\"rdp\" accept"; firewall-cmd --add-rich-rule="$r" && firewall-cmd --permanent --add-rich-rule="$r"
```

`set-credentials` спросит логин (у нас `view`) и пароль RDP. **Набирай пароль в английской раскладке.**
Если стереть кириллицу Backspace, в пароле останутся обрывки байтов, а `grdctl` всё равно ответит
«успешно».

## 15. Игры

**Что ставим.**

- **RetroDECK** — эмуляторы PS1, PS2, PS3, PSP и других консолей в одном пакете с меню для геймпада.
- **Steam** — игры для Linux и Windows через Proton.
- **Steam Link и Moonlight** — стрим игр с мощного ПК. У нас на ПК стоит Apollo (форк Sunshine), поток
  3840×2160 при 120 к/с в AV1, 150 Мбит/с. Настройка сервера и клиента, сеть и MikroTik —
  [streaming.md](streaming.md).
- **steam-devices** — права на геймпады (DualSense Edge и другие) для пользователя у экрана.

```bash
L=192.168.0.0/24
V="runuser -u view -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
dnf -y install steam-devices steam && udevadm trigger --subsystem-match=hidraw
flatpak install -y --noninteractive flathub net.retrodeck.retrodeck com.valvesoftware.SteamLink com.moonlight_stream.Moonlight
r="rule family=\"ipv4\" source address=\"$L\" service name=\"steam-streaming\" accept"; firewall-cmd --add-rich-rule="$r" && firewall-cmd --permanent --add-rich-rule="$r"
R=/root/atrium/rootfs; install -m 644 $R/etc/sysctl.d/90-atrium-stream.conf /etc/sysctl.d/ && sysctl -p /etc/sysctl.d/90-atrium-stream.conf
```

`90-atrium-stream.conf` увеличивает буфер приёма UDP: 4K-поток Steam Link переполнял стандартный.

**Первый запуск RetroDECK** — у ТВ, мастер есть только в графике. Выбери Custom Location и в окне выбора
**выдели** `/srv/games`: окно не берёт папку, в которой стоишь. RetroDECK сам допишет `/retrodeck`, туда
же лягут ROM'ы, BIOS и сохранения. По сети это `\\atrium.lan\media\games\retrodeck\roms\<система>`.
Прошивки PS3 и PS Vita мастер ставит сам. BIOS PS1 и PS2 положи в `bios/` — свои, снятые со своей
консоли.

**Правки RetroArch.** Делать только при **закрытом** RetroArch: при выходе он переписывает свой файл.

- **Полный экран при масштабе 250 %.** RetroArch просит поверхность 3840×2160 в логических пикселях, и
  окно уезжает за экран. Указываем логический размер экрана: 3840/2,5 × 2160/2,5 = 1536×864. При другом
  масштабе пересчитай.
- **Звук через PipeWire.** С `pulse` он трещал.
- **Геймпады через udev.**
- **Крестик = OK**, по-европейски.
- **Аналоговые стики в PS1 (SwanStation)** включены всегда.

```bash
pkill -u view -x retroarch; while pgrep -u view -x retroarch >/dev/null; do sleep 1; done
c=/home/view/.var/app/net.retrodeck.retrodeck/config/retroarch
\cp -p $c/retroarch.cfg $c/retroarch.cfg.bak-$(date +%Y%m%d) && \cp -p $c/retroarch-core-options.cfg $c/retroarch-core-options.cfg.bak-$(date +%Y%m%d)
sed -i -e 's/^video_fullscreen_x = .*/video_fullscreen_x = "1536"/' -e 's/^video_fullscreen_y = .*/video_fullscreen_y = "864"/' -e 's/^audio_driver = .*/audio_driver = "pipewire"/' -e 's/^input_joypad_driver = .*/input_joypad_driver = "udev"/' -e 's/^menu_swap_ok_cancel_buttons = .*/menu_swap_ok_cancel_buttons = "true"/' $c/retroarch.cfg
sed -i 's/^swanstation_Controller1_ForceAnalog = .*/swanstation_Controller1_ForceAnalog = "true"/' $c/retroarch-core-options.cfg
grep -nE '^(video_fullscreen_[xy]|audio_driver|input_joypad_driver|menu_swap_ok_cancel_buttons) ' $c/retroarch.cfg
```

Выход из игры в RetroArch — Ctrl+Q. Меню в игре — L3+R3. Файлы `.cue` с путями Windows внутри не
запускаются: в первой строке должно быть `FILE "<имя>.bin" BINARY`.

## 16. Ловушка на зависания

**Зачем.** Бокс завис ночью, когда экран был выключен, и не оставил никаких следов (12.10; похожий
случай 07.10 мог иметь внешнюю причину). Ловушка
сделает так, что в следующий раз он перезагрузится сам и оставит отчёт:

- **аппаратный сторожевой таймер** материнской платы (SP5100 TCO): если ядро не отзывается 60 секунд,
  плата перезагружает бокс;
- **при зависании процессора или ошибке ядра — паника**, через 10 секунд перезагрузка;
- **отчёт о панике** пишется в память UEFI (pstore), после загрузки systemd переносит его в
  `/var/lib/systemd/pstore`. Заставка при входе по SSH покажет это красной строкой `pstore`;
- **GFXOFF выключен** (`amdgpu.ppfeaturemask` без бита `0x8000`). Глубокий сон видеоядра при выключенном
  экране — один из подозреваемых. Боксу от розетки это засыпание графики не нужно (экономия — доли ватта),
  поэтому оставляем выключенным насовсем. Параметр ядра добавлен на шаге 12.

```bash
R=/root/atrium/rootfs
if [ -e /etc/systemd/system.conf ]; then echo "system.conf exists - add RuntimeWatchdogSec=60 under [Manager] by hand"; else install -m 644 $R/etc/systemd/system.conf /etc/systemd/system.conf; fi
install -m 644 $R/etc/sysctl.d/90-atrium-lockup.conf /etc/sysctl.d/ && sysctl -p /etc/sysctl.d/90-atrium-lockup.conf
systemctl daemon-reexec && systemctl show -p RuntimeWatchdogUSec && cat /sys/class/watchdog/watchdog0/state
```

Что смотреть после зависания — в [problems.md](problems.md), раздел «Ночные зависания».

## 17. Заставка с данными при входе по SSH

При входе по SSH сразу видно: аптайм, память, оба диска с температурой, сеть, горит ли экран, упавшие
службы и отчёты ловушки. `atrium-login.sh` вызывает `/usr/local/sbin/atrium-motd` — это тот же файл в
`/usr/local/bin` (ссылка `sbin` → `bin`, см. шаг про `atrium-sysload`).

```bash
R=/root/atrium/rootfs
install -m 755 $R/usr/local/bin/atrium-motd /usr/local/bin/atrium-motd
install -m 644 $R/etc/profile.d/atrium-login.sh /etc/profile.d/atrium-login.sh
restorecon /usr/local/bin/atrium-motd /etc/profile.d/atrium-login.sh
```

## 18. Перезагрузка, экран и проверка

```bash
reboot
```

**Экран.** Если ТВ и подключение те же, что у нас (LG C3 в HDMI бокса, в GNOME это `HDMI-1`),
`monitors.xml` из шага 9 уже задаёт 3840×2160 при 120 Гц, масштаб 250 % и SDR. Иначе выставь это у ТВ в
«Настройки → Дисплеи». HDR вручную не включай: его включает mpv на HDR-видео (шаг 9, «Авто-HDR»). Пока HDR
включён, в быстром меню есть ползунок яркости HDR. Заводская нейтраль — 100 %, мы держим около 110 %. При
каждом включении HDR ползунок снова встаёт на 100 %.

**Проверка.** Всё должно быть зелёным:

```bash
V="runuser -u view -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
systemctl --failed; systemctl --user -M view@ --failed
cat /proc/cmdline; aplay -l | grep ^card
findmnt /srv; ls -ldZ /srv
vainfo --display drm 2>&1 | grep -c VAProfile
$V gnome-extensions list --enabled --details | grep -cE "State: ACTIVE"
systemctl is-active transmission-daemon smb wsdd atrium-sysload; systemctl --user -M view@ is-active atrium-screensaver gnome-remote-desktop
firewall-cmd --list-all
cat /sys/class/watchdog/watchdog0/state
```

Ожидаемо:

- нет упавших служб;
- в `/proc/cmdline` есть четыре наших параметра;
- в `aplay -l` один ЦАП;
- `/srv` смонтирован;
- профилей VA-API больше десятка;
- девять расширений ACTIVE;
- все службы active;
- watchdog в состоянии `active`.

Дальше — [обновления и что после них проверять](updates.md).
