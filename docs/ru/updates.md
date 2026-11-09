# Обновления: что может отлететь и как вернуть

[English version](../en/updates.md) · [Установка](install.md) · [Железо](hardware.md) · [Известные проблемы](problems.md) · [Вывод на ТВ](tv-output.md)

## Как обновляемся

**Бокс обновляется сам, раз в сутки** — `atrium-update` ([установка, шаг 20](install.md)): с 07:00, пока
боксом никто не пользуется, ставит всё из репозиториев и flatpak, проверяет `atrium-check`, пишет письма до
и после, перезагружается, если нужно. Без шага 20 — то же самое руками из консоли.

| Что | Как обновляется |
|---|---|
| Система и программы из репозиториев | `atrium-update` (`dnf update -y`) или руками `dnf upgrade`; перезагрузка, если обновилось ядро, mesa или GNOME |
| Spotify, RetroDECK, Steam Link, Moonlight | `atrium-update` (`flatpak update -y`) или руками `flatpak update` |
| Расширения GNOME в `/usr/local/share/gnome-shell/extensions` | сами не обновляются никогда; новую версию ставим руками, как при установке |
| Unified Remote | RPM без репозитория, `dnf` его не трогает; новая версия — вручную, потом заново патч (ниже) |
| Windscribe | RPM без репозитория; новая стабильная версия — с GitHub (Windscribe/Desktop-App), сверить sha256 из описания релиза, `dnf install ./…rpm` |

gnome-software и PackageKit **не установлены**, поэтому на ТВ никогда не всплывёт «доступны
обновления». GNOME не проверяет обновления расширений (`allow-extension-installation false`).

Три правила:

1. **`dnf remove` — сначала с `--assumeno`.** dnf удаляет и «осиротевшие» зависимости. Так однажды ушли
   файловый менеджер и `tuned`.
2. **Никогда `--allowerasing`.** Раз в несколько недель `dnf update` пишет
   `Problem: … nothing provides mesa-filesystem(x86-64) = X needed by mesa-va-drivers-freeworld-X …` и ниже
   `Skipping packages with broken dependencies: mesa-va-drivers-freeworld`. **Это уведомление, не ошибка:**
   транзакция проходит, всё остальное ставится, видео работает на прежней паре mesa и freeworld. Причина —
   две половины одного драйвера из двух репозиториев: freeworld грузит ядро Mesa из файла с версией в имени
   (`libgallium-26.2.4.so`) и обязан совпадать с ним точно, поэтому RPM Fusion требует ту же версию
   `mesa-filesystem`. Собирает он против mesa из Fedora **updates-testing** и выкладывает сразу, а Fedora держит
   mesa в testing 5–7 дней — это окно и есть «Skipping». Ничего не делать: через неделю `dnf update` поставит
   обе половины вместе. Где mesa сейчас (`testing` или `stable`, с какого числа):
   ```bash
   curl -s -H 'Accept: application/json' 'https://bodhi.fedoraproject.org/updates/?packages=mesa&releases=F45&rows_per_page=3' | python3 -c "import sys,json; [print(u['title'], u['status'], 'testing', (u.get('date_testing') or '-')[:10], 'stable', (u.get('date_stable') or '-')[:10]) for u in json.load(sys.stdin)['updates']]"
   ```
   Обратный случай — Fedora выложила mesa, а freeworld ещё нет — выглядит как пропуск самой mesa; ждать так
   же. С `--allowerasing` dnf удалит freeworld, и видео станет декодировать процессор.
3. После обновления ядра, mesa или GNOME — перезагрузка и проверка (ниже). `atrium-update` делает это сам.

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
- `/etc/postfix/main.cf`, `/etc/postfix/header_checks`, `/etc/aliases` (почта, шаг 20)
- метки SELinux `file_contexts.local`

Репозиторий Chrome с Fedora 45 лежит в `/usr/share/dnf5/repos.d/google-chrome.repo` (пакет
`fedora-workstation-repositories`), а «включён» — наша строка в `/etc/dnf/repos.override.d/99-config_manager.repo`
(её пишет `dnf config-manager setopt google-chrome.enabled=1`). Старый `/etc/yum.repos.d/google-chrome.repo`
после перехода остался как `.rpmsave` — его удалили.

`/etc/systemd/system.conf`, `/etc/locale.conf` и `/etc/default/grub` пакет вообще не ставит
(`%ghost`), так что их обновление не трогает.

**Обновление перезапишет:**

| Файл | Когда | Что вернётся | Как починить |
|---|---|---|---|
| `/etc/chromium/master_preferences` | если Fedora поменяет этот файл в пакете chromium; наш уйдёт в `.rpmsave` | стартовая страница Fedora, но только в **новом** профиле Chromium | `install -m 644 /root/atrium/rootfs/etc/chromium/master_preferences /etc/chromium/` |
| 5 пультов в `/opt/urserver/remotes` | при установке новой версии urserver | короткий тап не кликает; заглавные, кириллица и символы не печатаются | патч заново (ниже) |
| `extension.js` GJS OSK | при установке новой версии GJS OSK | нет кнопки EN/RU на экранной клавиатуре | патч заново (ниже) |

Наоборот, **не обновятся** копии ярлыков Chrome и Chromium у пользователя ТВ
(`~/.local/share/applications/{google-chrome,chromium-browser}.desktop`, русский интерфейс, шаг 8): если
пакет поменяет свой ярлык (новый пункт меню, другая строка запуска), копия останется старой. Повторить
команду из шага 8.

После каждого обновления такие файлы разбираем штатной утилитой `rpmconf` (пакет `rpmconf`): по каждому
`.rpmnew` она показывает разницу и спрашивает — оставить наш (`N`), взять новый (`Y`) или слить (`M`), а
второй запуск с `-c` находит «осиротевшие» `.rpmnew/.rpmsave` от удалённых пакетов и удаляет их. В системе
таких файлов не должно оставаться: `atrium-check` предупреждает о каждом.

```bash
rpmconf -a && rpmconf -a -c
find / -xdev \( -path /proc -o -path /sys -o -path /srv \) -prune -o \( -name '*.rpmnew' -o -name '*.rpmsave' -o -name '*.rpmorig' \) -print
```

Бывает, `rpmconf` пишет над вопросом верное имя файла (`Configuration file '/etc/postfix/main.cf'`), а в
самом вопросе — чужое (`*** aliases`). Верить надо строке `Configuration file`.

## Что может перестать работать

Наши собственные файлы пакеты не трогают, но новые версии программ могут их «не понять».

1. **Новая версия Fedora = новый GNOME — главный риск.** GNOME выключает расширения, у которых в
   `metadata.json` нет его версии. Сейчас все наши объявляют GNOME 51:
   - наши три (`atrium-lock`, `atrium-brightness-value`, `atrium-no-dnd-icon`) — 50 и 51;
   - Executor (v32), GJS OSK (релиз 8761dd7 с GitHub) и Desktop Widgets (v21) — до 51;
   - Dash to Dock, Freon и Just Perfection стоят пакетами Fedora и обновляются вместе с системой.
2. **Наши расширения используют внутренности gnome-shell**: ползунок яркости, меню Freon, виджеты
   Desktop Widgets, значок «Не беспокоить». Они могут сломаться и на обновлении внутри GNOME 51.x. Тогда
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
11. **Авто-HDR** (`atrium-hdr`, `auto-hdr.lua`) опирается на `gdctl` и свойство `color-mode` в D-Bus
    DisplayConfig — это GNOME. После обновления GNOME проверь от `view`: `atrium-hdr status` отвечает `sdr`,
    а HDR-фильм в mpv включает и выключает HDR.
12. **`atrium-hdmi-keep`** (если включён, [установка, шаг 19](install.md)): параметры `drm.edid_firmware=`
    и `video=` новые ядра берут из `/etc/kernel/cmdline`, а файл с описанием экрана
    `/usr/lib/firmware/edid/atrium-tv.bin` попадает в initramfs каждого нового ядра через
    `/etc/dracut.conf.d/90-atrium-hdmi-keep.conf` — всё само, при установке ядра. Что может сломать:
    (а) ядро переименует параметр или перестанет понимать `video=…:e` — тогда в `status` строка `kernel
    log: 0 x 'forcing …'`; (б) ты поменял ТВ или его настройку, меняющую EDID, — файл устарел, пересохранить:
    `off`, перезагрузка, `on`, перезагрузка. После обновления ядра — `atrium-hdmi-keep status`.

## Проверка после обновления

Всё одной командой — `atrium-check`. Её же запускают `atrium-update` перед перезагрузкой и
`atrium-boot-notify` после загрузки:

```bash
atrium-check        # после обновления, до перезагрузки
atrium-check boot   # после загрузки: ещё ядро, с которым загрузились, и вывод на ТВ
```

Что проверяет:

- наши параметры ядра (четыре, шесть с `atrium-hdmi-keep`) — в `/etc/kernel/cmdline` и во всех записях
  загрузки; у ядра следующей загрузки — EDID ТВ в initramfs, если keep включён. Ядро следующей загрузки не
  готово — код выхода 2, и `atrium-update` не перезагружается;
- упавших служб нет — ни системных, ни в сеансе ТВ;
- все расширения GNOME `ACTIVE`;
- VA-API даёт H.264, HEVC 10-bit и AV1, mesa и freeworld одной версии;
- звуковая карта одна — ЦАП;
- нет `.rpmnew` и `.rpmsave`;
- наши `master_preferences` Chromium и `policies.json` Firefox на месте, оба префа ещё есть в Firefox;
- копии ярлыков Chrome и Chromium совпадают с системными, кроме строки Exec;
- настройки Transmission: только TCP, без DHT и LPD, шифрование обязательно, остановка после закачки;
- патч Unified Remote — 5 пультов;
- патч GJS OSK — кнопка EN/RU;
- наши правки в `retroarch.cfg`;
- с `boot`: ядро загружено с нашими параметрами, вывод на ТВ (HDMI 2.1 FRL или «ТВ выключен»).

Последняя строка — `Problems:  none` или список. То же самое руками:

```bash
V="runuser -u view -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
uname -r; cat /proc/cmdline
systemctl --failed; systemctl --user -M view@ --failed
$V gnome-extensions list --enabled --details | grep -E "^[a-z]|State"
vainfo --display drm 2>&1 | grep -E "VAProfile(H264|HEVC|AV1)" | head -4
cat /sys/kernel/debug/dri/0000:05:00.0/amdgpu_dm_dtn_log | sed -n '/^HPO:/,/^$/p'
cat /proc/asound/cards
find /etc -name '*.rpmnew' -o -name '*.rpmsave'
rpm -V urserver | grep remotes
atrium-hdmi-keep status
```

Ожидаемо:

- четыре наших параметра ядра на месте (шесть, если включён `atrium-hdmi-keep`: тогда в его `status` —
  `configured: on`, `active now: on`, в initramfs 1 копия файла);
- нет упавших служб;
- все расширения `ACTIVE`;
- профили VA-API есть;
- в `/proc/asound/cards` один ЦАП;
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

## Вернуть патч GJS OSK

После установки новой версии GJS OSK (кнопка EN/RU; `atrium-check` пишет `GJS OSK: patch NOT in place`):

```bash
cd /usr/local/share/gnome-shell/extensions/gjsosk@vishram1123.com && patch -p1 --dry-run < /root/atrium/patches/gjsosk/atrium-gjsosk.patch && patch -p1 --backup --suffix=.orig < /root/atrium/patches/gjsosk/atrium-gjsosk.patch
```

Кнопка появится со следующего входа (перезагрузка). Если `--dry-run` ругается, автор переписал верхнюю
полосу клавиатуры: правку переносить руками — функция `atriumLangButton` и её вызов справа от кнопки
настроек, в обеих ветках `buildUI` (обычная и разделённая клавиатура).

## Переход на новую версию Fedora

Так перешли с 44 на 45 (06.11.2026). Не в день выхода. Всё, что можно, делаем и проверяем ещё на старой
версии: отката назад Fedora не умеет.

**Подготовка (на старой версии, с перезагрузкой и проверкой после каждого пункта):**

1. Все расширения должны объявлять новый GNOME. Чужие — новые версии (на 45: Executor 32 с
   extensions.gnome.org, GJS OSK — релиз с GitHub, см. [установку](install.md), шаг 10). Наши три — `"51"` в
   `shell-version`, но сначала сверить с исходниками нового gnome-shell те места, куда они лезут (на 51.1
   сверено: ползунок яркости и его подпись, OSD, быстрое меню, значок «Не беспокоить» — без изменений). Новые
   версии ставим ещё на старом GNOME и проверяем, что настройки на месте (`dconf dump` до и после).
2. У RPM Fusion есть репозиторий новой версии, и `mesa-va-drivers-freeworld` в нём совпадает с mesa Fedora.
3. Пробный прогон — ничего не ставит, показывает, что заменится и удалится:
   `dnf --releasever=45 --assumeno distro-sync`.
4. **Связка ключей.** С Fedora 45 её хранит oo7 вместо gnome-keyring. При автовходе ему нужен пароль связки
   в systemd-credential ([установка](install.md), шаг 6). Без него oo7 со второй загрузки держит связку
   запертой: Chrome выходит со всех сайтов, RDP не находит пароль. Credential кладём заранее. Связку,
   которую gnome-keyring создал под именем `Default_Keyring`, переименовываем в стандартную `login` —
   **только прямо перед перезагрузкой в обновление**: gnome-keyring связку `login` при автовходе запирает.

**Переход:**

```bash
systemctl disable --now atrium-update.timer && dnf system-upgrade download --releasever=45
K=/home/view/.local/share/keyrings && mv -f $K/Default_Keyring.keyring $K/login.keyring && printf login > $K/default && dnf5 offline reboot
```

Новый ключ Fedora (`Importing OpenPGP key`) сверить с https://fedoraproject.org/security/. Бокс ставит
обновление сам (15–30 минут) и перезагружается в новую версию.

**После перехода, до второй перезагрузки:**

1. `atrium-check boot` — Problems: none.
2. Журнал oo7: `Unlocking session keyring with systemd credential` и `Successfully migrated v0 keyring
   'login'`; связка открыта (`Locked false`), RDP и Chrome работают.
3. Конфиги: `rpmconf -a && rpmconf -a -c` (на 45 было два файла: `postfix/main.cf.rpmnew` — оставили наш и
   подняли `compatibility_level` до 3.11; `google-chrome.repo.rpmsave` — удалили).
4. Пакеты: `remove-retired-packages 44` (на 45 удалять было нечего), `dnf autoremove --assumeno` и, если
   список понятный, `dnf autoremove` (на 45 ушли gcr3 от gnome-keyring и ещё 7 ненужных), `dnf clean all`.
   «Битые» симлинки из `symlinks -r /usr` не трогать: все они принадлежат установленным пакетам.
5. Flatpak: `flatpak update`, неиспользуемые среды — `flatpak uninstall --unused`.
6. Мусор: старые `.bak`, старая связка открытым текстом (`login.keyring` и `login.keyring.migrated` рядом с
   `v1/`) — удалить, когда всё проверено. В конце `find` из раздела выше — ноль.
7. Вторая перезагрузка: в журнале oo7 `Unlocked keyring 'login'` — связка открылась паролем из credential.
8. `systemctl enable --now atrium-update.timer`.
