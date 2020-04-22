let radius, circumference, element;

const setProgress = percent => {
    const offset = circumference - percent / 100 * circumference;
    element.style.strokeDashoffset = offset;
}

export const counterProgress = (circle, minValue, maxValue) => {

    debugger;

    const input = $(`#${circle.attr('data-input')}`)[0];
    element = circle[0];
    radius = element.r.baseVal.value;
    circumference = radius * 2 * Math.PI;

    element.style.strokeDasharray = `${circumference} ${circumference}`;
    element.style.strokeDashoffset = `${circumference}`;

    setProgress(input.value);

    input.addEventListener('change', () => {
        debugger;
        // if (input.value.length < maxValue && input.value.length > minValue) {
            setProgress(input.value.length);
        // }
    })
}
