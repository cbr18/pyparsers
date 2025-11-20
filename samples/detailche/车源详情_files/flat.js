Array.prototype.flat = function(count) {
  let c = count || 1;
  let len = this.length;
  let ret = [];
  if (this.length == 0) return this;
  while (c--) {
    let _arr = [];
    let flag = false;
    if (ret.length == 0) {
      flag = true;
      for (let i = 0; i < len; i++) {
        if (this[i] instanceof Array) {
          ret.push(...this[i]);
        } else {
          ret.push(this[i]);
        }
      }
    } else {
      for (let i = 0; i < ret.length; i++) {
        if (ret[i] instanceof Array) {
          flag = true;
          _arr.push(...ret[i]);
        } else {
          _arr.push(ret[i]);
        }
      }
      ret = _arr;
    }
    if (!flag && c == Infinity) {
      break;
    }
  }
  return ret;
};
