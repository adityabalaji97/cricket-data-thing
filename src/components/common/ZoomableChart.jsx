import React from 'react';
import { Box, IconButton, Tooltip } from '@mui/material';
import ZoomOutMapIcon from '@mui/icons-material/ZoomOutMap';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';

const ZoomableChart = ({
  children,
  maxScale = 6,
  minScale = 1,
  initialScale = 1,
  isMobile = false,
}) => (
  <Box sx={{ position: 'relative', width: '100%', height: '100%' }}>
    <TransformWrapper
      initialScale={initialScale}
      minScale={minScale}
      maxScale={maxScale}
      centerOnInit
      limitToBounds={false}
      wheel={{ step: 0.08 }}
      pinch={{ step: 5 }}
      panning={{ velocityDisabled: true }}
      doubleClick={{ mode: 'reset' }}
    >
      {({ resetTransform }) => (
        <>
          <Tooltip title="Reset zoom">
            <IconButton
              size={isMobile ? 'small' : 'medium'}
              onClick={() => resetTransform()}
              sx={{
                position: 'absolute',
                top: 8,
                right: 8,
                zIndex: 2,
                bgcolor: 'rgba(255, 255, 255, 0.92)',
                border: '1px solid',
                borderColor: 'divider',
                '&:hover': { bgcolor: 'rgba(255, 255, 255, 1)' },
              }}
            >
              <ZoomOutMapIcon fontSize={isMobile ? 'small' : 'medium'} />
            </IconButton>
          </Tooltip>
          <TransformComponent
            wrapperStyle={{ width: '100%', height: '100%' }}
            contentStyle={{ width: '100%', height: '100%' }}
          >
            <Box sx={{ width: '100%', height: '100%' }}>
              {children}
            </Box>
          </TransformComponent>
        </>
      )}
    </TransformWrapper>
  </Box>
);

export default ZoomableChart;

