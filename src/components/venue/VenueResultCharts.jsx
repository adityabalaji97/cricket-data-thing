import React from 'react';
import { Box, Typography, useMediaQuery, useTheme } from '@mui/material';
import { colors as hsColors } from '../../theme/hindsightDark';

/**
 * The ground's results split and first-innings benchmarks, shared by the classic preview
 * (VenueNotes) and the story cards (src/components/story/visuals). Moved out of VenueNotes
 * unchanged.
 */
// bare: inside a story card, which supplies its own title.
const WinPercentagesPie = ({ data, bare = false }) => {
    const theme = useTheme();
    const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

    const noResults = Math.max(
        (data.total_matches || 0) - (data.batting_first_wins || 0) - (data.batting_second_wins || 0),
        0
    );

    const segments = [
        {
            key: 'bat-first',
            label: 'Bat first',
            value: data.batting_first_wins || 0,
            color: '#2563eb',
        },
        {
            key: 'no-result',
            label: 'NR',
            value: noResults,
            color: hsColors.textFaint,
        },
        {
            key: 'bowl-first',
            label: 'Bowl first',
            value: data.batting_second_wins || 0,
            color: '#f59e0b',
        },
    ];

    const totalMatches = segments.reduce((sum, segment) => sum + segment.value, 0);
    return (
        <Box sx={{ width: '100%', display: 'flex', flexDirection: 'column', gap: isMobile ? 1.5 : 2.5, px: { xs: 1, sm: 0 }, py: { xs: 0.75, sm: 1.5 } }}>
            {!bare && (
                <Typography variant={isMobile ? "body2" : "subtitle1"} sx={{ fontWeight: 700, textAlign: isMobile ? 'center' : 'left' }}>
                    Results Split
                </Typography>
            )}
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 1, textAlign: 'center' }}>
                {segments.map((segment) => {
                    const percentage = totalMatches > 0 ? (segment.value / totalMatches) * 100 : 0;
                    return (
                        <Box key={segment.key}>
                            <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', fontWeight: 700 }}>
                                {segment.label}
                            </Typography>
                            <Typography variant={isMobile ? "h5" : "h4"} sx={{ mt: 0.25, fontWeight: 700 }}>
                                {segment.value}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                {percentage.toFixed(0)}%
                            </Typography>
                        </Box>
                    );
                })}
            </Box>
            <Box sx={{ px: isMobile ? 0.25 : 0 }}>
                <Box sx={{
                    display: 'flex',
                    alignItems: 'center',
                    width: '100%',
                    minWidth: 0,
                    height: isMobile ? 18 : 20,
                    borderRadius: 999,
                    overflow: 'hidden',
                    bgcolor: hsColors.surface3,
                }}>
                    {totalMatches > 0 ? segments.map((segment) => (
                        segment.value > 0 ? (
                            <Box
                                key={segment.key}
                                sx={{
                                    height: '100%',
                                    flex: `${segment.value} 1 0`,
                                    minWidth: 0,
                                    bgcolor: segment.color,
                                }}
                            />
                        ) : null
                    )) : (
                        <Box sx={{ height: '100%', flex: '1 1 auto', bgcolor: hsColors.surface3 }} />
                    )}
                </Box>
            </Box>
        </Box>
    );
};

/**
 * "What total wins here": the venue's first-innings benchmarks on one scale.
 *
 * This replaced a back-to-back ECharts bar labelled "1st innings | 2nd innings" whose Winning and
 * Def/Chase rows were in fact all first-innings totals (average_chasing_score is the average target
 * that was chased down; highest_total_chased is a first-innings score) -- so half the chart was
 * drawn under the wrong heading. It also sat on fixed pixel gutters and %-placed labels. Each
 * benchmark is now a row with a dot on a shared scale, coloured by who won: blue = the side
 * batting first defended it, orange = it was chased down.
 */
const TOTAL_COLORS = { defended: '#3987e5', chased: '#d95926', neutral: hsColors.textLo };

const ScoresBarChart = ({ data, bare = false }) => {
    const rows = [
        { label: 'Lowest total defended', value: data.lowest_total_defended, kind: 'defended' },
        { label: 'Average target chased down', value: data.average_chasing_score, kind: 'chased' },
        { label: 'Average first innings', value: data.average_first_innings, kind: 'neutral' },
        { label: 'Average total defended', value: data.average_winning_score, kind: 'defended' },
        { label: 'Highest total chased', value: data.highest_total_chased, kind: 'chased' },
    ]
        .filter((row) => Number(row.value) > 0)
        .map((row) => ({ ...row, value: Math.round(Number(row.value)) }))
        .sort((x, y) => x.value - y.value);

    if (rows.length === 0) return null;

    const values = rows.map((row) => row.value);
    const lo = Math.floor((Math.min(...values) - 10) / 10) * 10;
    const hi = Math.ceil((Math.max(...values) + 10) / 10) * 10;
    const pos = (v) => `${((v - lo) / (hi - lo)) * 100}%`;
    const secondInnings = Math.round(Number(data.average_second_innings) || 0);

    return (
        <Box sx={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 1.25, py: { xs: 0.75, sm: 1.5 } }}>
            <Box sx={{ display: bare ? 'none' : 'block' }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>What total wins here</Typography>
                <Typography variant="body2" color="text.secondary">First-innings totals</Typography>
            </Box>
            <Box sx={{ display: 'grid', gap: 0.75 }}>
                {rows.map((row) => (
                    <Box
                        key={row.label}
                        sx={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.1fr) minmax(0, 1fr) 40px', alignItems: 'center', gap: 1.25, minHeight: 28 }}
                    >
                        <Typography sx={{ fontSize: '0.8125rem', color: 'text.secondary', lineHeight: 1.25 }}>{row.label}</Typography>
                        <Box sx={{ position: 'relative', height: 14 }}>
                            <Box sx={{ position: 'absolute', left: 0, right: 0, top: 6, height: 2, borderRadius: 1, bgcolor: 'rgba(255,255,255,0.08)' }} />
                            <Box
                                sx={{
                                    position: 'absolute',
                                    left: pos(row.value),
                                    top: 0,
                                    width: 14,
                                    height: 14,
                                    ml: '-7px',
                                    borderRadius: '50%',
                                    bgcolor: TOTAL_COLORS[row.kind],
                                    border: `2px solid ${hsColors.surface1}`,
                                }}
                            />
                        </Box>
                        <Typography sx={{ fontFamily: 'IBM Plex Mono, monospace', fontWeight: 600, fontSize: '0.875rem', textAlign: 'right' }}>
                            {row.value}
                        </Typography>
                    </Box>
                ))}
            </Box>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5, fontSize: '0.75rem', color: 'text.secondary' }}>
                <span><Box component="span" sx={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', bgcolor: TOTAL_COLORS.defended, mr: 0.75 }} />Batting side won</span>
                <span><Box component="span" sx={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', bgcolor: TOTAL_COLORS.chased, mr: 0.75 }} />Chased down</span>
                {secondInnings > 0 && <span>Average second innings: {secondInnings}</span>}
            </Box>
        </Box>
    );
};


export { ScoresBarChart, WinPercentagesPie };
