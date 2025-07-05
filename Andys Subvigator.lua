--------------------------------------------------
-- Roger Magnusson's Timecode Utility Functions --
--------------------------------------------------

--[[

MIT License

Copyright (c) 2023 Roger Magnusson

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

]]

local luaresolve, libavutil

luaresolve = {frame_rates = {
		get_fraction = function(self, frame_rate_string_or_number)
			local frame_rate = tonumber(tostring(frame_rate_string_or_number))
			local frame_rates = { 16, 18, 23.976, 24, 25, 29.97, 30, 47.952, 48, 50, 59.94, 60, 72, 95.904, 96, 100, 119.88, 120 }
			for _, current_frame_rate in ipairs (frame_rates) do
				if current_frame_rate == frame_rate or math.floor(current_frame_rate) == frame_rate then
					local is_decimal = current_frame_rate % 1 > 0
					local denominator = iif(is_decimal, 1001, 100)
					local numerator = math.ceil(current_frame_rate) * iif(is_decimal, 1000, denominator)
					return { num = numerator, den = denominator } end; end
			return nil, string.format("Invalid frame rate: %s", frame_rate_string_or_number) end,

		get_decimal = function(self, frame_rate_string_or_number)
			local fractional_frame_rate, error_message = self:get_fraction(frame_rate_string_or_number)
			if fractional_frame_rate ~= nil then return tonumber(string.format("%.3f", fractional_frame_rate.num / fractional_frame_rate.den))
			else return nil, error_message end; end, },

	load_library = function(name_pattern)
		local files = bmd.readdir(fu:MapPath("FusionLibs:"..iif(ffi.os == "Windows", "", "../"))..name_pattern)
		assert(#files == 1 and files[1].IsDir == false, string.format("Couldn't find exact match for pattern \"%s.\"", name_pattern))
		return ffi.load(files.Parent..files[1].Name)
	end,

	frame_from_timecode = function(self, timecode, frame_rate) return libavutil:av_timecode_init_from_string(timecode, self.frame_rates:get_fraction(frame_rate)).start end,

	timecode_from_frame = function(self, frame, frame_rate, drop_frame)
		return libavutil:av_timecode_make_string(0, frame, self.frame_rates:get_decimal(frame_rate), {
			AV_TIMECODE_FLAG_DROPFRAME = drop_frame == true or drop_frame == 1 or drop_frame == "1",
			AV_TIMECODE_FLAG_24HOURSMAX = true,
			AV_TIMECODE_FLAG_ALLOWNEGATIVE = false }) end }

libavutil = { library = luaresolve.load_library(iif(ffi.os == "Windows", "avutil*.dll", iif(ffi.os == "OSX", "libavutil*.dylib", "libavutil.so"))),
	demand_version = function(self, version)
		local library_version = self:av_version_info()
		return (library_version.major > version.major)
			or (library_version.major == version.major and library_version.minor > version.minor)
			or (library_version.major == version.major and library_version.minor == version.minor and library_version.patch > version.patch)
			or (library_version.major == version.major and library_version.minor == version.minor and library_version.patch == version.patch) end,

	set_declarations = function()
		ffi.cdef[[enum AVTimecodeFlag {
				AV_TIMECODE_FLAG_DROPFRAME      = 1<<0, // timecode is drop frame
				AV_TIMECODE_FLAG_24HOURSMAX     = 1<<1, // timecode wraps after 24 hours
				AV_TIMECODE_FLAG_ALLOWNEGATIVE  = 1<<2, // negative time values are allowed
			};

			struct AVRational { int32_t num; int32_t den; };
			struct AVTimecode { int32_t start; enum AVTimecodeFlag flags; struct AVRational rate; uint32_t fps; };

			char* av_timecode_make_string(const struct AVTimecode* tc, const char* buf, int32_t framenum);
			int32_t av_timecode_init_from_string(struct AVTimecode* tc, struct AVRational rate, const char* str, void* log_ctx);

			char* av_version_info (void);
		]]
	end,

	av_timecode_make_string = function(self, start, frame, fps, flags)
		local function bor_number_flags(enum_name, flags)
			local enum_value = 0    
			if (flags) then	for key, value in pairs(flags) do if (value == true) then enum_value = bit.bor(enum_value, tonumber(ffi.new(enum_name, key))) end; end; end
			return enum_value;
		end

		local tc = ffi.new("struct AVTimecode", {start = start,	flags = bor_number_flags("enum AVTimecodeFlag", flags),	fps = math.ceil(luaresolve.frame_rates:get_decimal(fps)) })

		if (flags.AV_TIMECODE_FLAG_DROPFRAME and fps > 60 and (fps % (30000 / 1001) == 0 or fps % 29.97 == 0)) and (not self:demand_version( { major = 4, minor = 4, patch = 0 } ))
		then frame = frame + 9 * tc.fps / 15 * (math.floor(frame / (tc.fps * 599.4))) + (math.floor((frame % (tc.fps * 599.4)) / (tc.fps * 59.94))) * tc.fps / 15 end

		local timecodestring = ffi.string(self.library.av_timecode_make_string(tc, ffi.string(string.rep(" ", 16)), frame))
	
		if (#timecodestring > 0) then
			local frame_digits = #tostring(math.ceil(fps) - 1)
			if frame_digits > 2 then timecodestring = string.format("%s%0"..frame_digits.."d", timecodestring:sub(1, timecodestring:find("[:;]%d+$")), tonumber(timecodestring:match("%d+$"))) end
			return timecodestring
		else return nil	end
	end,

	av_timecode_init_from_string = function(self, timecode, frame_rate_fraction)
		local tc = ffi.new("struct AVTimecode")
		local result = self.library.av_timecode_init_from_string(tc, ffi.new("struct AVRational", frame_rate_fraction), timecode, ffi.new("void*", nil))
		if (result == 0) then return { start = tc.start,
				flags =	{ AV_TIMECODE_FLAG_DROPFRAME = bit.band(tc.flags, ffi.C.AV_TIMECODE_FLAG_DROPFRAME) == ffi.C.AV_TIMECODE_FLAG_DROPFRAME,
					AV_TIMECODE_FLAG_24HOURSMAX = bit.band(tc.flags, ffi.C.AV_TIMECODE_FLAG_24HOURSMAX) == ffi.C.AV_TIMECODE_FLAG_24HOURSMAX,
					AV_TIMECODE_FLAG_ALLOWNEGATIVE = bit.band(tc.flags, ffi.C.AV_TIMECODE_FLAG_ALLOWNEGATIVE) == ffi.C.AV_TIMECODE_FLAG_ALLOWNEGATIVE, },
				rate =	{num = tc.rate.num, den = tc.rate.den }, fps = tc.fps }
		else error("avutil error code: "..result) end
	end,

	av_version_info = function(self)
		local version = ffi.string(self.library.av_version_info())
		return { major = tonumber(version:match("^%d+")),
			minor = tonumber(version:match("%.%d+"):sub(2)),
			patch = tonumber(version:match("%d+$"))	}
	end,
}

libavutil.set_declarations()



------------------------
-- Andy's Subvigator  --
------------------------

--[[MIT License

Copyright (c) 2023 andymees

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

]]
    
local ui = fu.UIManager
local disp = bmd.UIDispatcher(ui)

local lastTrack = 1
local subTrack = 1
local matchType = {MatchContains = true }
local requiresReturn = true
local dropFrame = false
local subsCount = 0
local mStep = 1
local offset = 1

-- Setup 'Subvigator' window
subvigator = disp:AddWindow({ID = 'MyWin', WindowTitle = "Andy's Subvigator", Geometry = {100, 100, 380, 700 }, Spacing = 0, ui.VGroup{ui.VGap(2), ui.HGroup{Weight = 0, ui.HGap(10), ui.Label{ID = 'Label', Text = 'Filter', Weight = 0.05 }, ui.LineEdit{ID = 'SearchText', PlaceholderText = 'Search Text Filter', Weight = 0.9, Events = {TextChanged = true, ReturnPressed = true }, }, ui:ComboBox{ID = 'SearchType', Weight = 0.05 }, }, ui.HGroup{Weight = 0, ui.HGap(24), ui:CheckBox{ID = 'useDynamic', Text = 'Dynamic search text', Weight = 99 }, ui:CheckBox{ID = 'useDrop', Text = 'DF navigation' }, }, ui.VGap(0), ui.Tree{ID = 'Tree', SortingEnabled = true, Events = {ItemClicked = true }, }, ui.VGap(2), ui.HGroup{Weight = 0, ui:ComboBox{ID = 'SearchTrack', Weight = 0.3, Events = {Activated = true }, }, ui.HGap(10), ui.Label{ID = 'Label2', Text = 'Combine Subs', Weight = 0 }, ui.ComboBox{ID = 'CombiSubs', Weight = 0.2}, ui.HGap(10), ui.Button{ID = 'refreshBtn', Text = 'Refresh', Weight = 0.5}, ui.HGap(10) }, }, })
local itm = subvigator:GetItems()

local projectManager = resolve:GetProjectManager()
local project = projectManager:GetCurrentProject()
local timeline = project:GetCurrentTimeline()
local framerate = timeline:GetSetting('timelineFrameRate')
local trackItems = timeline:GetItemListInTrack('subtitle', subTrack)
pcall(function () subsCount = #trackItems end)
local multiSubCount = math.floor(subsCount/mStep) -1
local zeroPad = '%0'..string.len(subsCount)..'d'

-- Add combo box options for track choice
local trackCount = timeline:GetTrackCount('subtitle')
for track = 0, trackCount-1 do itm.SearchTrack:AddItem('ST '..track+1) end

-- Add combo box items for search choice
itm.SearchType:AddItems({'Contains', 'Exact', 'Starts With', 'Ends With', 'Wildcard'})

-- Add combo box items for multisubs
itm.CombiSubs:AddItems({'1', '2', '3', '4', '5', '6', '7', '8', '9', '10'})

-- Add table header
local hdr = itm.Tree:NewItem()
hdr.Text[0] = '#'
hdr.Text[1] = 'Subtitle'
itm.Tree:SetHeaderItem(hdr)

-- Setup column widths
itm.Tree.ColumnCount = 2
itm.Tree.ColumnWidth[0] = 58
itm.Tree.ColumnWidth[1] = 280

-- Define function to add rows
local format = string.format
function populateTable(hide)
    for row = 1, subsCount, mStep do
        itRow = itm.Tree:NewItem()
        itRow.Text[0] = format(zeroPad, row)
        local multisub = ''
        pcall(function () for i=0, mStep-2 do multisub = multisub..trackItems[row+i]:GetName()..'\n' end; multisub = multisub..trackItems[row+mStep-1]:GetName() end)
        itRow.Text[1] = multisub
        itRow.Text[2] = tostring(trackItems[row]:GetStart())
        itm.Tree:AddTopLevelItem(itRow)
        if (hide and not(itm.SearchText.Text == '')) then itRow:SetHidden(true) end
    end
end

-- Add rows (all visible)
populateTable(0)

-- Apply default sort
itm.Tree:SortItems(0,'AscendingOrder')

-- Move timeline playhead
function subvigator.On.Tree.ItemClicked(ev)
    timeline:SetCurrentTimecode(luaresolve:timecode_from_frame(tonumber(ev.item.Text[2]), framerate, dropFrame))
end

-- Filter for search text
function subvigator.On.SearchText.ReturnPressed(ev)
    local searchText = itm.SearchText.Text
    local hits = itm.Tree:FindItems(searchText, matchType, 1)
    if (searchText == '') then for row = 0, multiSubCount do itm.Tree:TopLevelItem(row):SetHidden(false) end
    else
        for row = 0, multiSubCount do itm.Tree:TopLevelItem(row):SetHidden(true) end
        for hit = 1, #hits do itm.Tree:TopLevelItem(math.floor(hits[hit].Text[0]/mStep)-offset):SetHidden(false) end
    end
end

-- Filter for search text - conditional (dynamic filtering)
function subvigator.On.SearchText.TextChanged(ev)
    if (requiresReturn) then else subvigator.On.SearchText.ReturnPressed() end
end

-- Change search type
function subvigator.On.SearchType.CurrentIndexChanged(ev)
    if itm.SearchType.CurrentIndex == 0 then matchType = {MatchContains = true }
    elseif itm.SearchType.CurrentIndex == 1 then matchType = {MatchExactly = true }
    elseif itm.SearchType.CurrentIndex == 2 then matchType = {MatchStartsWith = true }
    elseif itm.SearchType.CurrentIndex == 3 then matchType = {MatchEndsWith = true }
    elseif itm.SearchType.CurrentIndex == 4 then matchType = {MatchWildcard = true } end
    subvigator.On.SearchText.ReturnPressed()
end

-- Change search track
function subvigator.On.SearchTrack.Activated(ev)
    subTrack = itm.SearchTrack.CurrentIndex +1
    if (not(subTrack == lastTrack)) then lastTrack = subTrack; subvigator.On.refreshBtn.Clicked() end
end

-- Change multi sub value
function subvigator.On.CombiSubs.CurrentIndexChanged(ev)
    mStep = itm.CombiSubs.CurrentIndex +1
    if mStep > 1 then offset = 0 else offset = 1 end
    subvigator.On.refreshBtn.Clicked()
end

-- Toggle dynamic filtering
function subvigator.On.useDynamic.Clicked(ev)
    requiresReturn = not(itm.useDynamic.Checked)
    subvigator.On.SearchText.TextChanged()
end

-- Toggle drop frame status
function subvigator.On.useDrop.Clicked(ev)
    dropFrame = itm.useDrop.Checked
end

-- Refresh table
function subvigator.On.refreshBtn.Clicked(ev)
    project = projectManager:GetCurrentProject()
    timeline = project:GetCurrentTimeline()
    framerate = timeline:GetSetting('timelineFrameRate')
    trackCount = timeline:GetTrackCount('subtitle')
    trackItems = timeline:GetItemListInTrack('subtitle', subTrack)
    if (not(pcall(function () subsCount = #trackItems end))) then subsCount = 0 end
    multiSubCount = math.floor(subsCount/mStep) -1
    zeroPad = '%0'..string.len(subsCount)..'d'
    
    itm.SearchTrack:Clear()
    for track = 0, trackCount-1 do itm.SearchTrack:AddItem('ST '..track+1) end

    -- Remove all rows and repopulate table
    itm.Tree:Clear()
    populateTable(1)
    
    -- Apply default sort
    itm.Tree:SortItems(0,'AscendingOrder')
    itm.SearchTrack.CurrentIndex = lastTrack-1

    -- Filter for search text
    local searchText = itm.SearchText.Text
    local hits = itm.Tree:FindItems(searchText, matchType, 1)
    if (not(itm.SearchText.Text == '')) then
        for hit = 1, #hits do itm.Tree:TopLevelItem(math.floor(hits[hit].Text[0]/mStep)-offset):SetHidden(false) end
    end
end

-- The window was closed
function subvigator.On.MyWin.Close(ev) disp:ExitLoop() end

subvigator:Show()
disp:RunLoop()
subvigator:Hide()
