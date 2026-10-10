// Published starting points for about 3 mm (1/8 in) plywood, checked Oct 2026.
// Each machine uses its own speed/power scale, so rows are not comparable to each other.
export const LASER = {
  checked: 'Oct 2026',
  rows: [
    { machine: 'Epilog Fusion, 60 W CO2', kind: 'CO2',
      cut: 'Speed 10%, power 100%, frequency 10, 1 pass, air assist on',
      engrave: '300 DPI, speed 50%, power 100%',
      source: 'Epilog Fusion material settings (generic wood)', url: 'https://makerspace.aapld.org/wp-content/uploads/2024/06/fusion-material-settings-50-watt.pdf' },
    { machine: 'NYC Resistor Epilog, 60 W CO2', kind: 'CO2',
      cut: 'Speed 100, power 50 (their scale; 1/8 in birch)',
      engrave: 'Speed 100, power 40',
      source: 'NYC Resistor laser power wiki', url: 'https://wiki.nycresistor.com/wiki/Laser_Power' },
    { machine: 'Glowforge Pro, CO2', kind: 'CO2',
      cut: 'Speed 200–220, full power, 1 pass (owner reports)',
      engrave: 'Speed 600, power 80, 225 LPI',
      source: 'Glowforge community thread on 3 mm Baltic birch', url: 'https://community.glowforge.com/t/3mm-1-8-baltic-birch-settings/79487' },
    { machine: 'xTool D1 Pro, 20 W diode', kind: 'diode',
      cut: 'Power 100%, 6 mm/s, 1 pass (3 mm basswood plywood)',
      engrave: 'Power 60%, 100 mm/s',
      source: 'xTool material settings (now the Atomm Materials Lab)', url: 'https://www.atomm.com/materials-lab/official' },
    { machine: 'xTool D1 Pro, 10 W diode', kind: 'diode',
      cut: 'Power 100%, 3 mm/s, 2 passes',
      engrave: 'No published value found; test on the coupon',
      source: 'xTool material settings (now the Atomm Materials Lab)', url: 'https://www.atomm.com/materials-lab/official' },
  ],
};
