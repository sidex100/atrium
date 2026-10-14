-- auto-hdr.lua - HDR on the TV only while mpv plays an HDR video (atrium).
-- 2026-10-13: the desktop stays SDR (in HDR GNOME re-composes every frame and the GPU has no headroom).
-- When a PQ or HLG video starts: pause, switch the screen to HDR (atrium-hdr on), resume after 2 s.
-- When the video is over (mpv idle) or mpv quits: back to SDR. If the screen was already in HDR before
-- (turned on by hand), it is left alone. The TV blanks for 1-2 s on every switch (HDMI mode change).

local switched = false   -- HDR was turned on by this script
local busy = false

local function run(...)
    local r = mp.command_native({name = "subprocess", args = {"atrium-hdr", ...},
                                 capture_stdout = true, capture_stderr = true, playback_only = false})
    if r.status ~= 0 then
        mp.msg.warn("atrium-hdr " .. table.concat({...}, " ") .. " failed: " .. (r.stderr or ""))
    end
    return r
end

local function is_hdr(p)
    return p ~= nil and (p.gamma == "pq" or p.gamma == "hlg")
end

local function back_to_sdr()
    if switched then
        run("off")
        switched = false
    end
end

mp.observe_property("video-params", "native", function(_, p)
    if p == nil or busy then
        return
    end
    if is_hdr(p) and not switched then
        local st = run("status")
        if st.status == 0 and (st.stdout or ""):match("hdr") then
            return   -- HDR is already on (set by hand) - not ours to switch back
        end
        busy = true
        local was_paused = mp.get_property_native("pause")
        mp.set_property_native("pause", true)
        if run("on").status == 0 then
            switched = true
        end
        mp.add_timeout(2, function()
            if not was_paused then
                mp.set_property_native("pause", false)
            end
            busy = false
        end)
    elseif not is_hdr(p) and switched then
        back_to_sdr()   -- the next file in the playlist is SDR
    end
end)

mp.observe_property("idle-active", "bool", function(_, idle)
    if idle then
        back_to_sdr()
    end
end)

mp.register_event("shutdown", back_to_sdr)
