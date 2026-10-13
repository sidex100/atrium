-- 2026-10-04 atrium: on-screen keyboards (Keyboard, Keyboard (Russian), Keyboard (Function), ...)
-- reworked for Linux/uinput: every key types its own character whatever layout is active on atrium
-- (typing code shared with Core/Input), Shift and Caps work like on a phone, Ctrl/Alt/Win combos
-- are sent as separate key events. Original: keyboard.lua.bak-20261004.
-- Built by src/urserver/build.py (repository atrium) from keyboard.tmpl.lua; do not edit on the box.
local server = libs.server;
local keyboard = libs.keyboard;

keys = {};
weights = {};
texts = {};
icons = {};

@@ATRIUM_TYPING@@

-- on-screen Cyrillic keys are capitals; lower/upper pairs come from the ru tables above
local RU_LOWER = {};
local RU_UPPER = {};
do
	local by_key = {};
	for l, k in pairs(RU_KEYS) do by_key[k] = l; end
	for u, k in pairs(RU_SHIFT_KEYS) do RU_LOWER[u] = by_key[k]; RU_UPPER[by_key[k]] = u; end
end

-- Shift + digit or punctuation: as on the US layout, or as on the ru layout for Keyboard (Russian)
local US_SHIFTED = {
	["1"] = "!", ["2"] = "@", ["3"] = "#", ["4"] = "$", ["5"] = "%", ["6"] = "^", ["7"] = "&",
	["8"] = "*", ["9"] = "(", ["0"] = ")", ["-"] = "_", ["="] = "+", [","] = "<", ["."] = ">",
	["/"] = "?", [";"] = ":", ["'"] = "\"", ["["] = "{", ["]"] = "}", ["\\"] = "|", ["`"] = "~"
};
local RU_SHIFTED = {
	["1"] = "!", ["2"] = "\"", ["3"] = "\226\132\150", ["4"] = ";", ["5"] = "%", ["6"] = ":",
	["7"] = "?", ["8"] = "*", ["9"] = "(", ["0"] = ")", ["-"] = "_", ["="] = "+", ["."] = ","
};

local MODS = { "CONTROL", "MENU", "LWIN", "RMENU", "SHIFT" }; -- order of pressing
local mods = {};      -- sticky modifiers, one-shot: released after the next key
local caps = false;   -- Caps on the on-screen keyboard: capitals until tapped again
local russian = nil;  -- this remote shows Cyrillic keys

local function is_russian()
	if russian == nil then
		russian = false;
		for _, row in ipairs(keys) do
			for _, k in ipairs(row) do
				if RU_LOWER[k] then russian = true; end
			end
		end
	end
	return russian;
end

local function mark(key, on)
	server.update({ id = "key_" .. key, checked = on });
end

-- character of an on-screen key; nil for named keys (ESCAPE, TAB, BACK, RETURN, F1, ...)
local function char_of(key)
	if key == "AT" then return "@"; end
	if key == "COMMA" then return ","; end
	if key == "SPACE" then return " "; end
	if #key == 1 or not keyboard.iskey(key) then return key; end
	return nil;
end

local function clear_mods()
	for _, m in ipairs(MODS) do
		if mods[m] then mods[m] = nil; mark(m, false); end
	end
end

-- physical key with the sticky modifiers held, each as separate events
local function send_combo(name)
	local held = {};
	for _, m in ipairs(MODS) do
		if mods[m] then keyboard.down(m); table.insert(held, m); os.sleep(5); end
	end
	keyboard.down(name);
	os.sleep(10);
	keyboard.up(name);
	for i = #held, 1, -1 do os.sleep(5); keyboard.up(held[i]); end
end

actions.toggle = function (key)
	if key == "CAPITAL" then
		caps = not caps;
		mark(key, caps);
		return;
	end
	if keyboard.ismodifier(key) then
		if mods[key] then mods[key] = nil; mark(key, false); else mods[key] = true; mark(key, true); end
		return;
	end
	local ch = char_of(key);
	if ch == nil or mods.CONTROL or mods.MENU or mods.LWIN or mods.RMENU then
		-- named key or a combo (Ctrl+C, Alt+Tab, ...): the physical key with the held modifiers
		send_combo((ch and key_for(ch)) or key);
	else
		local lower = RU_LOWER[ch] or (ch:match("^%a$") and ch:lower());
		if lower then
			local upper = RU_UPPER[lower] or lower:upper();
			if (mods.SHIFT and not caps) or (caps and not mods.SHIFT) then ch = upper; else ch = lower; end
		elseif mods.SHIFT then
			ch = (is_russian() and RU_SHIFTED[ch]) or US_SHIFTED[ch] or ch;
		end
		type_text(ch, {});
	end
	mark(key, false);
	clear_mods();
end

@@PRELOAD@@
