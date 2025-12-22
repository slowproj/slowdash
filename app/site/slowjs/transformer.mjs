// transformer.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 27 September 2022 //


import { JG as $ } from './jagaimo/jagaimo.mjs';


class Functor {
    constructor(args) {
        this.args = args;
    }
    apply(data) {
        return data;
    }
};


class ScalarFunctor extends Functor {
    constructor(args) {
        super(args);
    }
    
    apply(data) {
        if (Array.isArray(data)) {
            let result = [];
            for (const xk of data) {
                result.push(this._applyToScalar(xk));
            }
            return result;
        }
        
        return this._applyToScalar(data);
    }

    _applyToScalar(data) {
        return data;
    }
};


class OffsetFunctor extends ScalarFunctor {
    constructor(args) {
        super(args);
        if (args.length < 1) {
            this.offset = 0;
        }
        else {
            this.offset = Number(args[0]);
        }
    }
    _applyToScalar(data) {
        return Number(data) + this.offset;
    }
};



class ScaleFunctor extends ScalarFunctor {
    constructor(args) {
        super(args);
        if (args.length < 1) {
            this.scale = 1;
        }
        else {
            this.scale = Number(args[0]);
        }
    }
    _applyToScalar(data) {
        return Number(data) * this.scale;
    }
};


class FormatFunctor extends ScalarFunctor {
    constructor(args) {
        super(args);
        if (args.length < 1) {
            this.format = '%s';
        }
        else {
            this.format = args[0];
        }
    }
    _applyToScalar(data) {
        return $.sprintf(this.format, data);
    }
};


class MatchFunctor extends ScalarFunctor {
    constructor(args) {
        super(args);
        if (args.length < 1) {
            this.regex = null;
        }
        else {
            this.regex = new RegExp(args[0], args[1]);
        }
    }
    _applyToScalar(data) {
        if (! this.regex) {
            return false;
        }
        if ((data === null) || (data === undefined)) {
            return null;
        }
        return this.regex.test(data);
    }
};


class ReplaceFunctor extends ScalarFunctor {
    constructor(args) {
        super(args);
        if (args.length < 1) {
            this.target = null;
        }
        else {
            this.target = args[0];
        }
        if (args.length < 2) {
            this.substitute = null;
        }
        else {
            this.substitute = args[1];
        }
    }
    _applyToScalar(data) {
        if (data == this.target) {
            return this.substitute;
        }
        else {
            return data;
        }
    }
};


class EqualFunctor extends ScalarFunctor {
    constructor(args) {
        super(args);
        if (args.length > 0) {
            this.rhs = args[0];
        }
        else {
            this.rhs = null;
        }
    }
    _applyToScalar(data) {
        if ((data === null) || (data === undefined) || (this.rhs === null)) {
            return null;
        }
        return data == this.rhs;
    }
};


class GreaterThanFunctor extends ScalarFunctor {
    constructor(args) {
        super(args);
        if (args.length > 0) {
            this.rhs = args[0];
        }
        else {
            this.rhs = null;
        }
    }
    _applyToScalar(data) {
        if ((data === null) || (data === undefined) || (this.rhs === null)) {
            return null;
        }
        return data > this.rhs;
    }
};


class InvertFunctor extends ScalarFunctor {
    constructor(args) {
        super(args);
    }
    _applyToScalar(data) {
        if ((data === null) || (data === undefined)) {
            return null;
        }
        return ! Boolean(data);
    }
};


class DefaultFunctor extends ScalarFunctor {
    constructor(args) {
        super(args);
        if (args.length > 0) {
            this.value = args[0];
        }
        else {
            this.value = undefined;
        }
    }
    _applyToScalar(data) {
        if (this.value === undefined) {
            return data;
        }
        if ((data === null) || (data === undefined)) {
            return this.value;
        }
        return data;
    }
};


class LastFunctor extends Functor {
    constructor(args) {
        super(args);
    }
    apply(data) {
        if (Array.isArray(data)) {
            if (data.length > 0) {
                return data[data.length-1];
            }
            else {
                return null;
            }
        }
        else {
            return data;
        }
    }
};


class GetFunctor extends Functor {
    constructor(args) {
        super(args);
    }
    
    apply(data) {
        if (this.args.length < 1) {
            return data;
        }
        if (data?.table) {
            return this._applyToTable(this.args[0], data);
        }
        else if (data?.tree) {
            return this._applyToTree(this.args[0], data);
        }
        else {
            return data;
        }
    }

    _applyToTable(column, data) {
        if (typeof(column) == 'string') {
            for (let k = 0; k < (data.columns ?? []).length; k++) {
                if (data.columns[k] == column) {
                    column = k;
                    break;
                }
            }
        }
        let result = [];
        for (const row of data.table ?? []) {
            result.push(row[column]);
        }
        return result;
    }
    
    _applyToTree(path, data) {
        let node = $.extend(true, {}, data.tree);
        for (const key of path.split('/')) {
            if ((node[key] === undefined) || (node[key] === null)) {
                console.log("path not found: " + path);
                return null;
            }
            node = node[key];
        }
        return node;
    }
};





let FunctorCollection = {
    // scalar functor //
    offset: OffsetFunctor,
    scale: ScaleFunctor,
    format: FormatFunctor,
    match: MatchFunctor,
    replace: ReplaceFunctor,
    eq: EqualFunctor,
    gt: GreaterThanFunctor,
    invert: InvertFunctor,
    'default': DefaultFunctor,
    // array functor //
    last: LastFunctor,
    // table/tree functor //
    get: GetFunctor,
};



export class Transformer {
    static decompose(name) {
        if (! name) {
            return { channel: null, transform: null };
        }
        const splited = name.split('->');
        let channel = splited[0];
        let transform = "";
        const bracketMatch = channel.match(/^ *([^\[]+)\[([^\]]+)\] *$/);
        if (bracketMatch) {
            channel = bracketMatch[1];
            transform += '->get(' + bracketMatch[2] + ')';
        }
        for (let i = 1; i < splited.length; i++) {
            transform += "->" + splited[i];
        }
        return {
            channel: channel,
            transform: new Transformer(transform)
        };
    }
    
    constructor(formula) {
        this.functorList = [];
        

        function parseValue(value) {
            if (
                (value.length > 2) &&
                ((value[0] == '"') || (value[0] == "'")) &&
                (value[value.length-1] == value[0])
            ){
                return value.substring(1, value.length-1);
            }
            else if (value == 'true') {
                return true;
            }
            else if (value == 'false') {
                return false;
            }
            else if (value == 'null') {
                return null;
            }
            else if (value == 'NaN') {
                return NaN;
            }
            else {
                const num = Number(value);
                if (isNaN(num)) {
                    return value;
                }
                return num;
            }
        }        

        for (let f of formula.split('->')) {
            const decompose = f.match(/^ *([a-zA-Z0-9]+)\((.*)\) *$/);
            if (! decompose || (decompose.length != 3)) {
                continue;
            }
            const name = decompose[1];
            let args = [], currentArg = '';
            let inSingleQuote = false, inDoubleQuote = false, nestCount = 0;
            for (let ch of decompose[2]) {
                if (! inDoubleQuote && (ch == "'")) {
                    inSingleQuote = ! inSingleQuote;
                }
                if (! inSingleQuote && (ch == '"')) {
                    inDoubleQuote = ! inDoubleQuote;
                }
                if (inSingleQuote || inDoubleQuote) {
                    currentArg += ch;
                }
                else {
                    if (ch == ',') {
                        args.push(parseValue(currentArg));
                        currentArg = '';
                    }
                    else if (ch != ' ') {
                        currentArg += ch;
                    }
                }
            }
            if (currentArg.length > 0) {
                args.push(parseValue(currentArg));
            }

            let functorClass = FunctorCollection[name];
            if (! functorClass) {
                console.log("ERROR: unknown transform functor: " + name);
                continue;
            }
            this.functorList.push(new functorClass(args));
        }
    }

    apply(data) {
        let result = data;
        for (let functor of this.functorList) {
            result = functor.apply(result);
        }
        
        return result;
    }
};
