// Prompts to try, grouped by the chart form they are meant to produce (services/pack_charts.py).
// Shared by the public /graphics page and the admin idea box. A form is offered only when the
// parsed query has the right shape, and the others still appear as options to switch to.
export const GRAPHIC_EXAMPLE_GROUPS = [
  {
    form: 'Ranked bars',
    hint: 'One stat, ranked',
    prompts: [
      ['Most sixes in the death overs in IPL 2025, 100+ balls', 'T20'],
      ['Best economy rates in the powerplay in the IPL since 2024, 300+ balls', 'T20'],
      ['Highest strike rates against spin in T20s since 2024, 200+ balls', 'T20'],
    ],
  },
  {
    form: 'Trend line',
    hint: 'One stat over seasons',
    prompts: [
      ['Virat Kohli impact per 100 balls by season since 2020', 'T20'],
      ['Jasprit Bumrah economy by season since 2018', 'T20'],
      ['Rohit Sharma strike rate in ODIs by year since 2015', 'ODI'],
    ],
  },
  {
    form: 'Scatter',
    hint: 'Two stats, many players',
    prompts: [
      ['Average v strike rate for T20 batters since 2024 with 1000+ balls', 'T20'],
      ['Dot ball % v boundary % for IPL batters since 2024, 500+ balls', 'T20'],
      ['Economy v strike rate for T20 bowlers since 2024, 600+ balls', 'T20'],
    ],
  },
  {
    form: 'Big number',
    hint: 'One standout figure',
    prompts: [
      ['ODI batters since 2019 averaging 50+ at a strike rate of 100+, by control %, 1000+ balls', 'ODI'],
      ['Shubman Gill strike rate among IPL openers since 2024, 500+ balls', 'T20'],
      ['Rashid Khan economy among T20 spinners since 2023, 1000+ balls', 'T20'],
    ],
  },
  {
    form: 'Above / below zero',
    hint: 'Value added or lost',
    prompts: [
      ['Virat Kohli impact per 100 balls by phase since 2024', 'T20'],
      ['Glenn Maxwell impact per 100 balls by season since 2018', 'T20'],
      ['MS Dhoni impact per 100 balls by season since 2019', 'T20'],
    ],
  },
  {
    form: 'Dumbbell',
    hint: 'Two splits per player',
    prompts: [
      ['IPL batters strike rate v pace and spin since 2024, 150+ balls', 'T20'],
      ['T20 batters average v pace and spin since 2024, 1000+ balls', 'T20'],
      ['IPL bowlers economy v left- and right-handed batters since 2024, 300+ balls', 'T20'],
    ],
  },
  {
    form: 'Stacked',
    hint: 'How a total is made up',
    prompts: [
      ['IPL batters runs by phase since 2024', 'T20'],
      ['IPL bowlers wickets by phase since 2024', 'T20'],
      ['T20 batters runs by phase since 2025, 1000+ balls', 'T20'],
    ],
  },
  {
    form: 'Field',
    hint: 'Where the runs go',
    prompts: [
      ['Virat Kohli runs by wagon zone since 2024', 'T20'],
      ['Suryakumar Yadav runs by wagon zone in T20s since 2023', 'T20'],
      ['Travis Head boundaries by wagon zone since 2024', 'T20'],
    ],
  },
];

// Flat list (first prompt per form), kept for callers that want one example each.
export const GRAPHIC_EXAMPLES = GRAPHIC_EXAMPLE_GROUPS.map((g) => [g.form, g.prompts[0][0], g.prompts[0][1]]);
