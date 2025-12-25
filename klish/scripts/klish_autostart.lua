-- /opt/netlab-cli/scripts/klish_autostart.lua

-- Build per-session state file path
local function iface_state_file()
  local uid = klish.context('uid') or "0"
  local pid = klish.context('pid') or "0"
  return string.format("/tmp/klish_iface_%s_%s", uid, pid)
end

local function write_iface(iface)
  if not iface or iface == "" then
    return
  end
  local f = io.open(iface_state_file(), "w")
  if not f then
    return
  end
  f:write(iface)
  f:close()
end

local function read_iface()
  local f = io.open(iface_state_file(), "r")
  if not f then
    return nil
  end
  local line = f:read("*l")
  f:close()
  if not line or line == "" then
    return nil
  end
  return line
end

local function delete_iface()
  os.remove(iface_state_file())
end

-- === EXPORTED HELPERS (called from XML) ===================

-- called from view_config "interface" action
function set_current_iface_from_param()
  local iface = klish.par("iface_name")
  write_iface(iface)
end

-- prompt for view_interface
function prompt_config_if()
  local iface = read_iface() or "?"
  io.write(string.format("NetLab(config-if-%s)# ", iface))
end

-- optional: clear state on exit
function clear_current_iface()
  delete_iface()
end

-- apply IP address in config-if view
function iface_set_ip()
  local iface = read_iface()
  if not iface then
    print("No interface selected.")
    return
  end

  local addr = klish.par("addr")
  if not addr or addr == "" then
    print("No IP address provided.")
    return
  end

  print(string.format("Configuring %s with IP %s...", iface, addr))
  os.execute(string.format('ip addr add %s dev %s', addr, iface))
end

-- shutdown in config-if view
function iface_shutdown()
  local iface = read_iface()
  if not iface then
    print("No interface selected.")
    return
  end
  print("Shutting down " .. iface .. "...")
  os.execute(string.format('ip link set dev %s down', iface))
end
