function name=ai700_filename(r)
name=sprintf('P%03d_f%03dHz_D%02d_P%03dto%03dW.mat',r.id,r.frequency_Hz,r.duty_percent,r.low_power_W,r.high_power_W);
end
