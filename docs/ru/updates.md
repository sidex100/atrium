# Обновления: что может отлететь и как вернуть

[English version](../en/updates.md) · [Установка](install.md) · [Железо](hardware.md) · [Известные проблемы](problems.md)

## Как обновляемся

**Только вручную из консоли**, ничего автоматического:

| Что | Как обновляется |
|---|---|
| Система и программы из репозиториев | `dnf upgrade`, потом перезагрузка, если обновилось ядро, mesa или GNOME |
| Spotify, RetroDECK, Steam Link, Moonlight | `flatpak update` |
| Расширения GNOME в `/usr/local/share/gnome-shell/extensions` | сами не обновляются никогда; новую версию ставим руками, как при установке |
| Unified Remote | RPM без репозитория, `dnf` его не трогает; новая версия — вручную, потом заново патч (ниже) |

gnome-software и PackageKit **не установлены**, поэтому на ТВ никогда не всплывёт «доступны
обновления». GNOME не проверяет обновления расширений (`allow-extension-installation false`).

Три правила:

1. **`dnf remove` — сначала с `--assumeno`.** dnf удаляет и «осиротевшие» зависимости. Так однажды ушли
   файловый менеджер и `tuned`.
2. **Никогда `--allowerasing`.** Если dnf пишет, что пропускает mesa из-за `mesa-va-drivers-freeworld`,
   значит RPM Fusion ещё не собрал драйвер под новую mesa. Подожди день-два. С `--allowerasing` dnf удалит
   драйвер, и видео станет декодировать процессор.
3. После обновления ядра, mesa или GNOME — перезагрузка и проверка (ниже).

## Что пакеты перезаписывают

Проверено `rpm -Va` на atrium (13.10.2026): из файлов пакетов изменены только эти.

**Обновление оставит наш файл.** Новую версию от пакета оно положит рядом как `.rpmnew` (это
`%config(noreplace)`):

- `/etc/samba/smb.conf`
- `/etc/sysconfig/wsdd`
- `/etc/gdm/custom.conf`
- `/etc/NetworkManager/NetworkManager.conf`
- `/etc/dnf/dnf.conf`
- `/etc/chrony.conf` (сюда установщик записал наш NTP-сервер)
- `/etc/yum.repos.d/google-chrome.repo` (его переписывает сам Chrome)
- метки SELinux `file_contexts.local`

`/etc/systemd/system.conf`, `/etc/locale.conf` и `/etc/default/grub` пакет вообще не ставит
(`%ghost`), так что их обновление не трогает.

**Обновление перезапишет:**

| Файл | Когда | Что вернётся | Как починить |
|---|---|---|---|
| `/etc/chromium/master_preferences` | если Fedora поменяет этот файл в пакете chromium; наш уйдёт в `.rpmsave` | стартовая страница Fedora, но только в **новом** профиле Chromium | `install -m 644 /root/atrium/rootfs/etc/chromium/master_preferences /etc/chromium/` |
| 5 пультов в `/opt/urserver/remotes` | при установке новой версии urserver | короткий тап не кликает; заглавные, кириллица и символы не печатаются | патч заново (ниже) |

Найти такие файлы после обновления:

```bash
find /etc -name '*.rpmnew' -o -name '*.rpmsave'
```

## Что может перестать работать

Наши собственные файлы пакеты не трогают, но новые версии программ могут их «не понять».

1. **Fedora 45 (GNOME 51) — главный риск.** GNOME выключает расширения, у которых в `metadata.json`
   нет его версии:
   - наши три (`atrium-lock`, `atrium-brightness-value`, `atrium-no-dnd-icon`) объявляют только 50;
   - Executor (v30) и GJS OSK (v53) — до 50;
   - Desktop Widgets (v21) уже поддерживает 51;
   - Dash to Dock, Freon и Just Perfection стоят пакетами Fedora и обновятся вместе с системой.
2. **Наши расширения используют внутренности gnome-shell**: ползунок яркости, меню Freon, виджеты
   Desktop Widgets, значок «Не беспокоить». Они могут сломаться и на обновлении внутри GNOME 50.x. Тогда
   расширение получает статус ERROR, гаджет просто перестаёт быть заблокированным или показывать число.
   Сеанс при этом не падает.
3. **Заставка** гасит экран через `org.gnome.Mutter.DisplayConfig.PowerSaveMode` и следит за простоем
   через `org.gnome.Mutter.IdleMonitor`. Если mutter их изменит, экран перестанет гаснеть.
4. **atrium-sysload** читает счётчики ядра `gpu_busy_percent` и `vcn_busy_percent`. Если их не станет, в
   панели будут нули.
5. **Аппаратное видео** зависит от того, совпадают ли версии `mesa-va-drivers-freeworld` (RPM Fusion) и
   mesa Fedora (см. правило 2).
6. **RetroDECK** при обновлении может предложить сбросить настройки и вернуть заводской `retroarch.cfg`.
   Тогда пропадут правки полного экрана, звука, геймпадов и кнопок. Повтори шаг 15 установки.
7. **Transmission** в новых версиях переименовывает настройки. Так в 4.1 `utp-enabled` перестал работать,
   и uTP выключается только через `preferred_transports: ["tcp"]`. После обновления посмотри журнал и
   `settings.json`.
8. **Ядро и linux-firmware** — это вывод на ТВ (HDMI 2.1) и стабильность. Старые ядра остаются в меню
   загрузки (`installonly_limit=3`), на них можно откатиться. Параметры ядра новые ядра берут из
   `/etc/kernel/cmdline`: проверено на 7.2.9-201.
9. **`amdgpu.ppfeaturemask=0xfff73fff`** задан полной маской. Если новое ядро добавит биты функций, маска
   может их случайно выключить или включить. Когда ловушка на зависания станет не нужна, параметр лучше
   убрать.
10. **`amdgpu.dcfeaturemask=0x402`** включает HDMI 2.1 (FRL) и тоже задан полной маской: `0x2` (умолчание
    ядра 7.2) + `0x400` (FRL). В ядре 7.4 FRL обещают включить по умолчанию вместе с VRR и ALLM. После
    перехода на 7.4 посмотри новое значение по умолчанию (`modinfo -p amdgpu`, исходник `amd_shared.h`) и,
    скорее всего, убери параметр: наша маска может выключить новые функции, которые 7.4 включает сам. Что
    после обновления ядра идёт именно HDMI 2.1 — проверка ниже и в [tv-output.md](tv-output.md).

## Проверка после обновления

```bash
V="runuser -u view -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
uname -r; cat /proc/cmdline
systemctl --failed; systemctl --user -M view@ --failed
$V gnome-extensions list --enabled --details | grep -E "^[a-z]|State"
vainfo --display drm 2>&1 | grep -E "VAProfile(H264|HEVC|AV1)" | head -4
cat /sys/kernel/debug/dri/0000:05:00.0/amdgpu_dm_dtn_log | sed -n '/^HPO:/,/^$/p'
aplay -l | grep ^card
find /etc -name '*.rpmnew' -o -name '*.rpmsave'
rpm -V urserver | grep remotes
```

Ожидаемо:

- три наших параметра ядра на месте;
- нет упавших служб;
- все расширения `ACTIVE`;
- профили VA-API есть;
- в `aplay -l` один ЦАП;
- `rpm -V urserver` показывает 5 изменённых пультов: значит, патч стоит.

## Вернуть патч Unified Remote

После установки новой версии urserver:

```bash
cd /opt/urserver/remotes/Unified && patch -p1 --dry-run < /root/atrium/patches/urserver/atrium-urserver.patch && patch -p1 --backup --suffix=.orig < /root/atrium/patches/urserver/atrium-urserver.patch
E="env HOME=/home/view XDG_SESSION_TYPE=wayland XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
runuser -u view -- $E /opt/urserver/urserver-stop; runuser -u view -- $E /opt/urserver/urserver-start --no-manager --no-notify
```

Если `--dry-run` ругается, производитель поменял эти файлы. Тогда правки нужно переносить руками: что
именно делает патч, описано в установке, шаг 14. Экранные клавиатуры собирает `src/urserver/build.py`.

## Переход на Fedora 45

Не в день выхода. Сначала:

1. На extensions.gnome.org проверь, вышли ли Executor и GJS OSK с поддержкой GNOME 51.
2. В `metadata.json` наших трёх расширений добавь `"51"` в `shell-version`, но только после проверки на
   GNOME 51: они используют внутренности оболочки.
3. Проверь, что у RPM Fusion есть репозиторий для 45 и `mesa-va-drivers-freeworld` в нём.

Сам переход штатный:

```bash
dnf upgrade --refresh && dnf system-upgrade download --releasever=45 && dnf offline reboot
```

После перехода — проверка выше и `dnf repolist` (RPM Fusion и Google Chrome должны быть на 45).
