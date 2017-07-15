import pytest
from numpy.testing import assert_allclose
import numpy as np
import scipy.sparse as sparse

from keras import backend as K
from keras.backend import theano_backend as KTH, floatx, set_floatx, variable
from keras.backend import tensorflow_backend as KTF
from keras.utils.conv_utils import convert_kernel
from keras.backend import cntk_backend as KC

BACKENDS = [KTH, KTF, KC]
# for special test cases of CNTK which treat dynamic axis
KCSD = 'CNTK_single_tensor_dynamicity'
KCTD = 'CNTK_two_tensor_dynamicity'


def check_dtype(var, dtype):
    if K._BACKEND == 'theano':
        assert var.dtype == dtype
    else:
        assert var.dtype.name == '%s_ref' % dtype


def cntk_func_single_tensor(function_name, x_shape, **kwargs):
    xc = KC.placeholder(x_shape)
    output_cntk = getattr(KC, function_name)(xc, **kwargs)
    return KC.function([xc], [output_cntk])


def cntk_func_two_tensor(function_name, x_shape, y, **kwargs):
    if type(y).__name__ == 'ndarray':
        xc = KC.placeholder(x_shape)
        output_cntk = getattr(KC, function_name)(xc, KC.variable(y), **kwargs)
        return KC.function([xc], [output_cntk])
    else:
        xc = KC.placeholder(ndim=len(x_shape))
        yc = KC.placeholder(y)
        output_cntk = getattr(KC, function_name)(xc, yc, **kwargs)
        return KC.function([xc, yc], [output_cntk])


def check_single_tensor_operation(function_name, input_shape, backend_list, **kwargs):
    val = np.random.random(input_shape) - 0.5

    z_list = []
    for k in backend_list:
        if k == KCSD:
            z = cntk_func_single_tensor(function_name, input_shape,
                                        **kwargs)([val])[0]
        else:
            z = k.eval(getattr(k, function_name)(k.variable(val), **kwargs))
        if hasattr(z, '_keras_shape'):
            assert z._keras_shape == z.shape
        z_list += [z]

    for (z1, z2) in zip(z_list[1:], z_list[:-1]):
        assert z1.shape == z2.shape
        assert_allclose(z1, z2, atol=1e-05)


def check_two_tensor_operation(function_name, x_input_shape,
                               y_input_shape, backend_list, **kwargs):
    xval = np.random.random(x_input_shape) - 0.5
    yval = np.random.random(y_input_shape) - 0.5

    z_list = []
    for k in backend_list:
        if k == KCSD:
            z = cntk_func_two_tensor(function_name, x_input_shape,
                                     y=yval, **kwargs)([xval])[0]
        elif k == KCTD:
            z = cntk_func_two_tensor(function_name, x_input_shape,
                                     y=y_input_shape, **kwargs)([xval, yval])[0]
        else:
            z = k.eval(getattr(k, function_name)(k.variable(xval), k.variable(yval), **kwargs))
        if hasattr(z, '_keras_shape'):
            assert z._keras_shape == z.shape
        z_list += [z]

    for (z1, z2) in zip(z_list[1:], z_list[:-1]):
        assert z1.shape == z2.shape
        assert_allclose(z1, z2, atol=1e-05)


def check_cross_entropy_with_valid_probability_distribution():
    xval = np.asarray([[0.26157712, 0.0432167], [-0.43380741, 0.30559841],
                       [0.20225059, -0.38956559], [-0.13805378, 0.08506755]], dtype=np.float32)
    xtf = KTF.variable(xval)
    xth = KTH.variable(xval)
    xc = KC.placeholder((4, 2))

    yval = np.asarray([[0.46221867, 0.53778133], [0.51228984, 0.48771016],
                       [0.64916514, 0.35083486], [0.47028078, 0.52971922]], dtype=np.float32)
    ytf = KTF.variable(yval)
    yth = KTH.variable(yval)
    yc = KC.placeholder((4, 2))

    ztf = KTF.eval(KTF.categorical_crossentropy(xtf, ytf, from_logits=True))
    zth = KTH.eval(KTH.categorical_crossentropy(xth, yth, from_logits=True))

    func_cntk = KC.function([xc, yc],
                            [KC.categorical_crossentropy(xc, yc, from_logits=True), ])
    zc = func_cntk([xval, yval])
    # Keras function return a list, take the first output
    assert len(zc) == 1
    zc = zc[0]

    assert zth.shape == ztf.shape
    assert_allclose(zth, ztf, atol=1e-05)

    assert ztf.shape == zc.shape
    assert_allclose(ztf, zc, atol=1e-05)


def check_composed_tensor_operations(first_function_name, first_function_args,
                                     second_function_name, second_function_args,
                                     input_shape, backend_list):
    val = np.random.random(input_shape) - 0.5
    x_list = [k.variable(val) for k in backend_list]
    y_list = []
    for x, k in zip(x_list, backend_list):
        y_list.append(getattr(k, first_function_name)(x, **first_function_args))

    z_list = []
    for y, k in zip(y_list, backend_list):
        z_list.append(k.eval(getattr(k, second_function_name)(y, **second_function_args)))

    for i in range(len(z_list) - 1):
        assert z_list[i].shape == z_list[i + 1].shape
        assert_allclose(z_list[i], z_list[i + 1], atol=1e-05)


class TestBackend(object):

    def test_is_keras_tensor(self):
        for K in [KTH, KTF]:
            np_var = np.array([1, 2])
            try:
                K.is_keras_tensor(np_var)
                assert True is False
            except ValueError:
                # This is the expected behavior
                continue

            keras_var = K.variable(np_var)
            assert K.is_keras_tensor(keras_var) is True
            keras_placeholder = K.placeholder(shape=(2, 4, 5))
            assert K.is_keras_tensor(keras_placeholder) is True

    def test_set_learning_phase(self):
        # not supported learning_phase
        for backend in (KTF, KTH):
            with pytest.raises(ValueError):
                backend.set_learning_phase(2)

    def test_eye(self):
        zth = KTH.eval(KTH.eye(3))
        ztf = KTF.eval(KTF.eye(3))
        assert zth.shape == ztf.shape
        assert_allclose(zth, ztf, atol=1e-05)

    def test_linear_operations(self):
        check_two_tensor_operation('dot', (4, 2), (2, 4), BACKENDS)
        check_two_tensor_operation('dot', (4, 2), (5, 2, 3), BACKENDS)

        check_two_tensor_operation('batch_dot', (4, 2, 3), (4, 5, 3), [KTF, KTH, KCTD], axes=(2, 2))
        check_two_tensor_operation('batch_dot', (4, 2, 3), (4, 3), [KTF, KTH, KCTD], axes=(2, 1))
        check_two_tensor_operation('batch_dot', (4, 2), (4, 2, 3), [KTF, KTH, KCTD], axes=(1, 1))
        check_two_tensor_operation('batch_dot', (32, 20), (32, 20), [KTF, KTH, KCTD], axes=1)
        check_two_tensor_operation('batch_dot', (32, 20), (32, 20), [KTF, KTH, KCTD], axes=(1, 1))

        check_single_tensor_operation('transpose', (4, 2), BACKENDS)
        # cntk doesn't support reverse yet
        check_single_tensor_operation('reverse', (4, 3, 2), [KTH, KTF], axes=1)
        check_single_tensor_operation('reverse', (4, 3, 2), [KTH, KTF], axes=(1, 2))

    def test_random_variables(self):
        zth = KTH.eval(KTH.random_uniform_variable((2, 3), 0, 1))
        ztf = KTF.eval(KTF.random_uniform_variable((2, 3), 0, 1))
        assert zth.shape == ztf.shape

        zth = KTH.eval(KTH.random_normal_variable((2, 3), 0, 1))
        ztf = KTF.eval(KTF.random_normal_variable((2, 3), 0, 1))
        assert zth.shape == ztf.shape

        # not supported dtype
        for dtype in ['int16', 'int32', 'int64', 'uint8', 'uint16', 'double']:
            with pytest.raises(ValueError):
                ztf = KTF.random_normal_variable((2, 3), 0, 1, dtype=dtype)

    def test_batch_dot_shape(self):
        x_batch = KTF.ones(shape=(32, 20))
        y_batch = KTF.ones(shape=(32, 20))
        xy_batch_dot = KTF.batch_dot(x_batch, y_batch, axes=1)
        assert_allclose(KTF.eval(xy_batch_dot), np.ones((32, 1)) * 20, atol=1e-05)
        xy_batch_dot = KTF.batch_dot(x_batch, y_batch, axes=0)
        assert_allclose(KTF.eval(xy_batch_dot), np.ones((20, 1)) * 32, atol=1e-05)
        # making sure swapping axes when ndim == 2 works
        x_batch = KTF.ones(shape=(32, 20))
        y_batch = KTF.ones(shape=(20, 32))
        xy_batch_dot = KTF.batch_dot(x_batch, y_batch, axes=(0, 1))
        assert_allclose(KTF.eval(xy_batch_dot), np.ones((20, 1)) * 32, atol=1e-05)
        xy_batch_dot = KTF.batch_dot(x_batch, y_batch, axes=(1, 0))
        assert_allclose(KTF.eval(xy_batch_dot), np.ones((32, 1)) * 20, atol=1e-05)

    def test_shape_operations(self):
        # concatenate
        xval = np.random.random((4, 3))
        x_list = [k.variable(xval) for k in BACKENDS]
        yval = np.random.random((4, 2))
        y_list = [k.variable(yval) for k in BACKENDS]
        z_list = []
        for x, y, k in zip(x_list, y_list, BACKENDS):
            z_list.append(k.eval(k.concatenate([x, y], axis=-1)))

        for i in range(len(z_list) - 1):
            assert z_list[i].shape == z_list[i + 1].shape
            assert_allclose(z_list[i], z_list[i + 1], atol=1e-05)

        check_single_tensor_operation('reshape', (4, 2), BACKENDS, shape=(8, 1))
        check_single_tensor_operation('permute_dimensions', (4, 2, 3), BACKENDS,
                                      pattern=(2, 0, 1))
        check_single_tensor_operation('repeat', (4, 1), BACKENDS, n=3)
        check_single_tensor_operation('flatten', (4, 1), BACKENDS)
        check_single_tensor_operation('batch_flatten', (20, 2, 5), [KTH, KTF, KCSD])
        check_single_tensor_operation('expand_dims', (4, 3), BACKENDS, axis=-1)
        check_single_tensor_operation('expand_dims', (4, 3, 2), BACKENDS, axis=1)
        check_single_tensor_operation('squeeze', (4, 3, 1), BACKENDS, axis=2)
        check_single_tensor_operation('squeeze', (4, 1, 1), BACKENDS, axis=1)
        check_composed_tensor_operations('reshape', {'shape': (4, 3, 1, 1)},
                                         'squeeze', {'axis': 2},
                                         (4, 3, 1, 1), BACKENDS)
        check_single_tensor_operation('temporal_padding',
                                      (4, 3, 3),
                                      BACKENDS)
        check_single_tensor_operation('temporal_padding',
                                      (4, 3, 3),
                                      BACKENDS,
                                      padding=(2, 2))
        check_single_tensor_operation('spatial_2d_padding',
                                      (4, 4, 3, 3),
                                      BACKENDS)
        check_single_tensor_operation('spatial_2d_padding',
                                      (4, 4, 3, 3),
                                      BACKENDS,
                                      padding=((2, 2), (2, 2)))
        check_single_tensor_operation('spatial_3d_padding',
                                      (4, 4, 3, 3, 3),
                                      BACKENDS)
        check_single_tensor_operation('spatial_3d_padding',
                                      (4, 4, 3, 3, 3),
                                      BACKENDS,
                                      padding=((2, 2), (2, 2), (2, 2)))

    def test_none_shape_operations(self):
        # Test shape inference when input
        # shape has `None` entries
        if K.backend() == 'theano':
            x = KTH.placeholder((3, None, 4))

            y = KTH.batch_flatten(x)
            if hasattr(y, '_keras_shape'):
                assert y._keras_shape == (3, None)

            y = KTH.flatten(x)
            if hasattr(y, '_keras_shape'):
                assert y._keras_shape == (None, )

    def test_repeat_elements(self):
        reps = 3
        for ndims in [1, 2, 3]:
            shape = np.arange(2, 2 + ndims)
            arr = np.arange(np.prod(shape)).reshape(shape)
            attr_list = [k.variable(arr) for k in BACKENDS]

            for rep_axis in range(ndims):
                np_rep = np.repeat(arr, reps, axis=rep_axis)
                z_list = []
                for a, k in zip(attr_list, BACKENDS):
                    z_list.append(k.eval(k.repeat_elements(a, reps, axis=rep_axis)))

                for z in z_list:
                    assert z.shape == np_rep.shape
                    assert_allclose(np_rep, z, atol=1e-05)
                    if hasattr(z, '_keras_shape'):
                        assert z._keras_shape == z.shape

                # test theano shape inference when
                # input shape has None entries
                if K.backend() == 'theano':
                    shape = list(shape)
                    shape[rep_axis] = None
                    x = K.placeholder(shape=shape)
                    y = K.repeat_elements(x, reps, axis=rep_axis)
                    assert y._keras_shape == tuple(shape)

        # Test invalid use cases
        with pytest.raises(ValueError):
            ztf = KTF.placeholder(shape=(None, 2, 3))
            KTF.repeat_elements(ztf, 5, axis=0)

    def test_tile(self):
        shape = (3, 4)
        arr = np.arange(np.prod(shape)).reshape(shape)
        attr_list = [k.variable(arr) for k in BACKENDS]

        n = (2, 1)
        z_list = []
        for a, k in zip(attr_list, BACKENDS):
            z_list.append(k.eval(k.tile(a, n)))

        for i in range(len(z_list) - 1):
            assert_allclose(z_list[i], z_list[i + 1], atol=1e-05)
            if hasattr(z_list[i], '_keras_shape'):
                assert z_list[i]._keras_shape == z_list[i].shape

        check_single_tensor_operation('tile', (2, 5), BACKENDS, n=[5, 2])

        # test theano shape inference when
        # input shape has None entries
        if K.backend() == 'theano':
            x = K.placeholder(shape=(None, 4))
            n = 2
            y = KTH.tile(x, n)
            assert y._keras_shape == (None, 8)
            n = (4, 3)
            y = K.tile(x, n)
            assert y._keras_shape == (None, 12)

    def test_gather(self):
        shape = (10, 2, 3)
        ref = np.arange(np.prod(shape)).reshape(shape)
        ref_th = KTH.variable(ref)
        ref_tf = KTF.variable(ref)

        inds = [1, 3, 7, 9]
        inds_th = KTH.variable(inds, dtype='int32')
        inds_tf = KTF.variable(inds, dtype='int32')
        th_z = KTH.gather(ref_th, inds_th)
        th_result = KTH.eval(th_z)
        tf_result = KTF.eval(KTF.gather(ref_tf, inds_tf))

        assert_allclose(tf_result, th_result, atol=1e-05)

        if hasattr(th_z, '_keras_shape'):
            assert th_z._keras_shape == th_result.shape

        # test theano shape inference when
        # input shape has None entries
        if K.backend() == 'theano':
            x = K.placeholder(shape=(None, 3, 4))
            indices = K.placeholder(shape=(5, 6), dtype='int32')
            y = K.gather(x, indices)
            assert y._keras_shape == (5, 6, 3, 4)

    def test_value_manipulation(self):
        val = np.random.random((4, 2))
        x_list = [k.variable(val) for k in BACKENDS]

        # get_value
        value_list = []
        for x, k in zip(x_list, BACKENDS):
            value_list.append(k.get_value(x))

        for i in range(len(value_list) - 1):
            assert value_list[i].shape == value_list[i + 1].shape
            assert_allclose(value_list[i], value_list[i + 1], atol=1e-05)

        # set_value
        value_list = []
        for x, k in zip(x_list, BACKENDS):
            value_list.append(k.get_value(x))

        for i in range(len(value_list) - 1):
            assert value_list[i].shape == value_list[i + 1].shape
            assert_allclose(value_list[i], value_list[i + 1], atol=1e-05)

        # count_params
        number_params_list = []
        for x, k in zip(x_list, BACKENDS):
            number_params_list.append(k.count_params(x))

        for i in range(len(number_params_list) - 1):
            assert number_params_list[i] == number_params_list[i + 1]

        # print_tensor
        check_single_tensor_operation('print_tensor', (), BACKENDS)
        check_single_tensor_operation('print_tensor', (2,), BACKENDS)
        check_single_tensor_operation('print_tensor', (4, 3), BACKENDS)
        check_single_tensor_operation('print_tensor', (1, 2, 3), BACKENDS)

        val = np.random.random((3, 2))
        x_list = [k.variable(val) for k in BACKENDS]
        shape_list = []
        for x, k in zip(x_list, BACKENDS):
            shape_list.append(k.get_variable_shape(x))

        for i in range(len(number_params_list) - 1):
            assert shape_list[i] == shape_list[i + 1]

    def test_elementwise_operations(self):
        check_single_tensor_operation('max', (4, 2), BACKENDS)
        check_single_tensor_operation('max', (4, 2), BACKENDS, axis=1, keepdims=True)

        check_single_tensor_operation('min', (4, 2), BACKENDS)
        check_single_tensor_operation('min', (4, 2), BACKENDS, axis=1, keepdims=True)
        check_single_tensor_operation('min', (4, 2, 3), BACKENDS, axis=[1, -1])

        check_single_tensor_operation('mean', (4, 2), BACKENDS)
        check_single_tensor_operation('mean', (4, 2), BACKENDS, axis=1, keepdims=True)
        check_single_tensor_operation('mean', (4, 2, 3), BACKENDS, axis=-1, keepdims=True)
        check_single_tensor_operation('mean', (4, 2, 3), BACKENDS, axis=[1, -1])

        check_single_tensor_operation('std', (4, 2), BACKENDS)
        check_single_tensor_operation('std', (4, 2), BACKENDS, axis=1, keepdims=True)
        check_single_tensor_operation('std', (4, 2, 3), BACKENDS, axis=[1, -1])

        check_single_tensor_operation('prod', (4, 2), BACKENDS)
        check_single_tensor_operation('prod', (4, 2), BACKENDS, axis=1, keepdims=True)
        check_single_tensor_operation('prod', (4, 2, 3), BACKENDS, axis=[1, -1])

        # cntk does not support cumsum and cumprod yet
        check_single_tensor_operation('cumsum', (4, 2), [KTF, KTH])
        check_single_tensor_operation('cumsum', (4, 2), [KTF, KTH], axis=1)

        check_single_tensor_operation('cumprod', (4, 2), [KTF, KTH])
        check_single_tensor_operation('cumprod', (4, 2), [KTF, KTH], axis=1)

        # does not work yet, wait for bool <-> int casting in TF (coming soon)
        # check_single_tensor_operation('any', (4, 2), [KTF, KTH])
        # check_single_tensor_operation('any', (4, 2), [KTF, KTH], axis=1, keepdims=True)
        #
        # check_single_tensor_operation('all', (4, 2), [KTF, KTH])
        # check_single_tensor_operation('all', (4, 2), [KTF, KTH],axis=1, keepdims=True)

        check_single_tensor_operation('any', (4, 2), [KC, KTH])
        check_single_tensor_operation('any', (4, 2), [KC, KTH], axis=1, keepdims=True)

        check_single_tensor_operation('all', (4, 2), [KC, KTH])
        check_single_tensor_operation('all', (4, 2), [KC, KTH], axis=1, keepdims=True)

        check_single_tensor_operation('argmax', (4, 2), BACKENDS)
        check_single_tensor_operation('argmax', (4, 2), BACKENDS, axis=1)

        check_single_tensor_operation('argmin', (4, 2), BACKENDS)
        check_single_tensor_operation('argmin', (4, 2), BACKENDS, axis=1)

        check_single_tensor_operation('square', (4, 2), BACKENDS)
        check_single_tensor_operation('abs', (4, 2), BACKENDS)
        check_single_tensor_operation('sqrt', (4, 2), BACKENDS)
        check_single_tensor_operation('exp', (4, 2), BACKENDS)
        # cntk return -85.1 for zero or negative number, not nan, so can't compare with other backend.
        check_single_tensor_operation('log', (4, 2), [KTH, KTF])
        check_single_tensor_operation('round', (4, 2), BACKENDS)
        check_single_tensor_operation('sign', (4, 2), BACKENDS)
        check_single_tensor_operation('pow', (4, 2), BACKENDS, a=3)
        check_single_tensor_operation('clip', (4, 2), BACKENDS, min_value=0.4,
                                      max_value=0.6)

        # two-tensor ops
        check_two_tensor_operation('equal', (4, 2), (4, 2), BACKENDS)
        check_two_tensor_operation('not_equal', (4, 2), (4, 2), BACKENDS)
        check_two_tensor_operation('greater', (4, 2), (4, 2), BACKENDS)
        check_two_tensor_operation('greater_equal', (4, 2), (4, 2), BACKENDS)
        check_two_tensor_operation('less', (4, 2), (4, 2), BACKENDS)
        check_two_tensor_operation('less_equal', (4, 2), (4, 2), BACKENDS)
        check_two_tensor_operation('maximum', (4, 2), (4, 2), BACKENDS)
        check_two_tensor_operation('minimum', (4, 2), (4, 2), BACKENDS)

    # cntk doesn't support gradient in this way
    def test_gradient(self):
        val = np.random.random((4, 2))
        x_list = [k.variable(val) for k in [KTH, KTF]]
        z_list = []
        zero_list = []
        for x, k in zip(x_list, [KTH, KTF]):
            exp = x * k.exp(x)
            loss = k.sum(exp)
            zero_loss = k.stop_gradient(loss)
            grad = k.gradients(loss, [exp])
            zero_grad = k.gradients(loss + zero_loss, [exp])
            z_list.append(k.eval(grad[0]))
            zero_list.append(k.eval(grad[0]))

        for i in range(len(z_list) - 1):
            assert z_list[i].shape == z_list[i + 1].shape
            assert zero_list[i].shape == zero_list[i + 1].shape
            assert_allclose(z_list[i], z_list[i + 1], atol=1e-05)
            assert_allclose(zero_list[i], zero_list[i + 1], atol=1e-05)
            assert_allclose(zero_list[i], z_list[i], atol=1e-05)
            assert_allclose(zero_list[i + 1], zero_list[i + 1], atol=1e-05)

    # cntk currently not support function in this way, so can't test as this
    def test_function(self):
        test_backend = [KTH, KTF]
        val = np.random.random((4, 2))
        input_val = np.random.random((4, 2))

        f_list = []
        x_list = []
        for k in test_backend:
            x = k.variable(val)
            x_list.append(x)
            y = k.placeholder(ndim=2)
            exp = k.square(x) + y
            update = x * 2
            f = k.function([y], [exp], updates=[(x, update)])
            f_list.append(f)

        function_outputs_list = [f([input_val])[0] for f in f_list]
        for i in range(len(function_outputs_list) - 1):
            assert function_outputs_list[i].shape == function_outputs_list[i + 1].shape
            assert_allclose(function_outputs_list[i], function_outputs_list[i + 1], atol=1e-05)

        new_val_list = []
        for x, k in zip(x_list, test_backend):
            new_val_list.append(k.get_value(x))

        for i in range(len(new_val_list) - 1):
            assert new_val_list[i].shape == new_val_list[i + 1].shape
            assert_allclose(new_val_list[i], new_val_list[i + 1], atol=1e-05)

    def test_rnn(self):
        # implement a simple RNN
        input_dim = 8
        output_dim = 4
        timesteps = 5

        input_val = np.random.random((32, timesteps, input_dim))
        init_state_val = np.random.random((32, output_dim))
        W_i_val = np.random.random((input_dim, output_dim))
        W_o_val = np.random.random((output_dim, output_dim))

        def rnn_step_fn(input_dim, output_dim, K):
            W_i = K.variable(W_i_val)
            W_o = K.variable(W_o_val)

            def step_function(x, states):
                assert len(states) == 1
                prev_output = states[0]
                output = K.dot(x, W_i) + K.dot(prev_output, W_o)
                return output, [output]

            return step_function

        # test default setup
        last_output_list = []
        outputs_list = []
        state_list = []

        unrolled_last_output_list = []
        unrolled_outputs_list = []
        unrolled_states_list = []

        backwards_last_output_list = []
        backwards_outputs_list = []
        backwards_states_list = []

        bwd_unrolled_last_output_list = []
        bwd_unrolled_outputs_list = []
        bwd_unrolled_states_list = []

        masked_last_output_list = []
        masked_outputs_list = []
        masked_states_list = []

        unrolled_masked_last_output_list = []
        unrolled_masked_outputs_list = []
        unrolled_masked_states_list = []

        for k in BACKENDS:
            rnn_fn = rnn_step_fn(input_dim, output_dim, k)
            inputs = k.variable(input_val)
            initial_states = [k.variable(init_state_val)]
            last_output, outputs, new_states = k.rnn(rnn_fn, inputs,
                                                     initial_states,
                                                     go_backwards=False,
                                                     mask=None)

            last_output_list.append(k.eval(last_output))
            outputs_list.append(k.eval(outputs))
            assert len(new_states) == 1
            state_list.append(k.eval(new_states[0]))
            # test unroll
            unrolled_last_output, unrolled_outputs, unrolled_new_states = k.rnn(
                rnn_fn, inputs,
                initial_states,
                go_backwards=False,
                mask=None,
                unroll=True,
                input_length=timesteps)

            unrolled_last_output_list.append(k.eval(unrolled_last_output))
            unrolled_outputs_list.append(k.eval(unrolled_outputs))
            assert len(unrolled_new_states) == 1
            unrolled_states_list.append(k.eval(unrolled_new_states[0]))

            backwards_last_output, backwards_outputs, backwards_new_states = k.rnn(rnn_fn, inputs,
                                                                                   initial_states,
                                                                                   go_backwards=True,
                                                                                   mask=None)
            backwards_last_output_list.append(k.eval(backwards_last_output))
            backwards_outputs_list.append(k.eval(backwards_outputs))
            assert len(backwards_new_states) == 1
            backwards_states_list.append(k.eval(backwards_new_states[0]))

            bwd_unrolled_last_output, bwd_unrolled_outputs, bwd_unrolled_new_states = k.rnn(
                rnn_fn, inputs,
                initial_states,
                go_backwards=True,
                mask=None,
                unroll=True,
                input_length=timesteps)

            bwd_unrolled_last_output_list.append(k.eval(bwd_unrolled_last_output))
            bwd_unrolled_outputs_list.append(k.eval(bwd_unrolled_outputs))
            assert len(bwd_unrolled_new_states) == 1
            bwd_unrolled_states_list.append(k.eval(bwd_unrolled_new_states[0]))

            np_mask = np.random.randint(2, size=(32, timesteps))
            mask = k.variable(np_mask)

            masked_last_output, masked_outputs, masked_new_states = k.rnn(
                rnn_fn, inputs,
                initial_states,
                go_backwards=False,
                mask=mask)
            masked_last_output_list.append(k.eval(masked_last_output))
            masked_outputs_list.append(k.eval(masked_outputs))
            assert len(masked_new_states) == 1
            masked_states_list.append(k.eval(masked_new_states[0]))

            unrolled_masked_last_output, unrolled_masked_outputs, unrolled_masked_new_states = k.rnn(
                rnn_fn, inputs,
                initial_states,
                go_backwards=False,
                mask=mask,
                unroll=True,
                input_length=timesteps)
            unrolled_masked_last_output_list.append(k.eval(unrolled_masked_last_output))
            unrolled_masked_outputs_list.append(k.eval(unrolled_masked_outputs))
            assert len(unrolled_masked_new_states) == 1
            unrolled_masked_states_list.append(k.eval(unrolled_masked_new_states[0]))

        for i in range(len(last_output_list) - 1):
            assert_allclose(last_output_list[i], last_output_list[i + 1], atol=1e-04)
            assert_allclose(outputs_list[i], outputs_list[i + 1], atol=1e-04)
            assert_allclose(state_list[i], state_list[i + 1], atol=1e-04)
            assert_allclose(backwards_states_list[i], backwards_states_list[i + 1], atol=1e-04)
            assert_allclose(backwards_last_output_list[i], backwards_last_output_list[i + 1], atol=1e-04)
            assert_allclose(backwards_outputs_list[i], backwards_outputs_list[i + 1], atol=1e-04)

        for l, u_l in zip(last_output_list, unrolled_last_output_list):
            assert_allclose(l, u_l, atol=1e-04)

        for o, u_o in zip(outputs_list, unrolled_outputs_list):
            assert_allclose(o, u_o, atol=1e-04)

        for s, u_s in zip(state_list, unrolled_states_list):
            assert_allclose(s, u_s, atol=1e-04)

        for b_l, b_u_l in zip(backwards_last_output_list, bwd_unrolled_last_output_list):
            assert_allclose(b_l, b_u_l, atol=1e-04)

        for b_o, b_u_o, in zip(backwards_outputs_list, bwd_unrolled_outputs_list):
            assert_allclose(b_o, b_u_o, atol=1e-04)

        for b_s, b_u_s in zip(backwards_states_list, bwd_unrolled_states_list):
            assert_allclose(b_s, b_u_s, atol=1e-04)

        for m_l, u_m_l, k in zip(masked_last_output_list, unrolled_masked_last_output_list, BACKENDS):
            # skip this compare on tensorflow
            if k != KTF:
                assert_allclose(m_l, u_m_l, atol=1e-04)

        for m_o, u_m_o, k in zip(masked_outputs_list, unrolled_masked_outputs_list, BACKENDS):
            # skip this compare on tensorflow
            if k != KTF:
                assert_allclose(m_o, u_m_o, atol=1e-04)

        for m_s, u_m_s, k in zip(masked_states_list, unrolled_masked_states_list, BACKENDS):
            if k != KTF:
                assert_allclose(m_s, u_m_s, atol=1e-04)

    def test_rnn_no_states(self):
        # implement a simple RNN without states
        input_dim = 8
        output_dim = 4
        timesteps = 5

        input_val = np.random.random((32, timesteps, input_dim))
        W_i_val = np.random.random((input_dim, output_dim))

        def rnn_step_fn(input_dim, output_dim, K):
            W_i = K.variable(W_i_val)

            def step_function(x, states):
                assert len(states) == 0
                output = K.dot(x, W_i)
                return output, []

            return step_function

        # test default setup
        last_output_list = []
        outputs_list = []

        for k in BACKENDS:
            rnn_fn = rnn_step_fn(input_dim, output_dim, k)
            inputs = k.variable(input_val)
            initial_states = []
            last_output, outputs, new_states = k.rnn(rnn_fn, inputs,
                                                     initial_states,
                                                     go_backwards=False,
                                                     mask=None)
            last_output_list.append(k.eval(last_output))
            outputs_list.append(k.eval(outputs))
            assert len(new_states) == 0

        for i in range(len(last_output_list) - 1):
            assert_allclose(last_output_list[i], last_output_list[i + 1], atol=1e-04)
            assert_allclose(outputs_list[i], outputs_list[i + 1], atol=1e-04)

    @pytest.mark.parametrize('x_np,axis,keepdims', [
        (np.array([1.1, 0.8, 0.9]), 0, False),
        (np.array([[1.1, 0.8, 0.9]]), 0, False),
        (np.array([[1.1, 0.8, 0.9]]), 1, False),
        (np.array([[1.1, 0.8, 0.9]]), -1, False),
        (np.array([[1.1, 0.8, 0.9]]), 1, True),
        (np.array([[1.1], [1.2]]), 0, False),
        (np.array([[1.1], [1.2]]), 1, False),
        (np.array([[1.1], [1.2]]), -1, False),
        (np.array([[1.1], [1.2]]), -1, True),
        (np.array([[1.1, 1.2, 1.3], [0.9, 0.7, 1.4]]), None, False),
        (np.array([[1.1, 1.2, 1.3], [0.9, 0.7, 1.4]]), 0, False),
        (np.array([[1.1, 1.2, 1.3], [0.9, 0.7, 1.4]]), 1, False),
        (np.array([[1.1, 1.2, 1.3], [0.9, 0.7, 1.4]]), -1, False),
    ])
    @pytest.mark.parametrize('K', [KTH, KTF], ids=["KTH", "KTF"])
    def test_logsumexp(self, x_np, axis, keepdims, K):
        '''
        Check if K.logsumexp works properly for values close to one.
        '''
        x = K.variable(x_np)
        assert_allclose(K.eval(K.logsumexp(x, axis=axis, keepdims=keepdims)),
                        np.log(np.sum(np.exp(x_np), axis=axis, keepdims=keepdims)),
                        rtol=1e-5)

    @pytest.mark.parametrize('K', [KTF], ids=["KTF"])
    def test_logsumexp_optim(self, K):
        '''
        Check if optimization works.
        '''
        x_np = np.array([1e+4, 1e-4])
        assert_allclose(K.eval(K.logsumexp(K.variable(x_np), axis=0)),
                        1e4,
                        rtol=1e-5)

    def test_switch(self):
        val = np.random.random()
        z_list = []
        for k in BACKENDS:
            x = k.variable(val)
            x = k.switch(k.greater_equal(x, 0.5), x * 0.1, x * 0.2)
            z_list.append(k.eval(x))

        for i in range(len(z_list) - 1):
            assert z_list[i].shape == z_list[i + 1].shape
            assert_allclose(z_list[i], z_list[i + 1], atol=1e-05)

    def test_nn_operations(self):
        check_single_tensor_operation('relu', (4, 2), BACKENDS, alpha=0.1, max_value=0.5)
        check_single_tensor_operation('softmax', (4, 10), BACKENDS)
        check_single_tensor_operation('softplus', (4, 10), BACKENDS)
        check_single_tensor_operation('elu', (4, 10), BACKENDS, alpha=0.5)

        check_single_tensor_operation('sigmoid', (4, 2), BACKENDS)
        check_single_tensor_operation('hard_sigmoid', (4, 2), BACKENDS)
        check_single_tensor_operation('tanh', (4, 2), BACKENDS)

        # dropout
        val = np.random.random((100, 100))
        x_list = [k.variable(val) for k in BACKENDS]
        z_list = []
        for x, k in zip(x_list, BACKENDS):
            z_list.append(k.eval(k.dropout(x, level=0.2)))

        for i in range(len(z_list) - 1):
            assert z_list[i].shape == z_list[i + 1].shape
            # dropout patterns are different, only check mean
            assert np.abs(z_list[i].mean() - z_list[i + 1].mean()) < 0.05

        check_two_tensor_operation('binary_crossentropy', (4, 2), (4, 2), BACKENDS, from_logits=True)
        # cross_entropy call require the label is a valid probability distribution,
        # otherwise it is garbage in garbage out...
        # due to the algo difference, we can't guarantee CNTK has the same result on the garbage input.
        # so create a seperate test case for valid lable input
        check_two_tensor_operation('categorical_crossentropy', (4, 2), (4, 2), [KTH, KTF], from_logits=True)
        check_cross_entropy_with_valid_probability_distribution()
        check_two_tensor_operation('binary_crossentropy', (4, 2), (4, 2), BACKENDS, from_logits=False)
        check_two_tensor_operation('categorical_crossentropy', (4, 2), (4, 2), BACKENDS, from_logits=False)

        check_single_tensor_operation('l2_normalize', (4, 3), BACKENDS, axis=-1)
        check_single_tensor_operation('l2_normalize', (4, 3), BACKENDS, axis=1)

        # Test invalid use cases
        for x, k in zip(x_list, [KTH, KTF]):
            with pytest.raises(ValueError):
                z = k.dropout(x, level=-0.5)

    def test_in_top_k(self):
        batch_size = 20
        num_classes = 10

        # Random prediction test case
        predictions = np.random.random((batch_size, num_classes)).astype('float32')
        targets = np.random.randint(num_classes, size=batch_size, dtype='int32')

        predictions_th = KTH.variable(predictions, dtype='float32')
        targets_th = KTH.variable(targets, dtype='int32')
        predictions_tf = KTF.variable(predictions, dtype='float32')
        targets_tf = KTF.variable(targets, dtype='int32')

        # (k == 0 or k > num_classes) does not raise an error but just return an unmeaningful tensor.
        for k in range(0, num_classes + 1):
            res_th = KTH.eval(KTH.in_top_k(predictions_th, targets_th, k))
            res_tf = KTF.eval(KTF.in_top_k(predictions_tf, targets_tf, k))

            assert res_th.shape == res_tf.shape
            assert_allclose(res_th, res_tf, atol=1e-05)

        # Identical prediction test case:
        # randomly set half of the predictions to an identical value
        num_identical = num_classes // 2
        for i in range(batch_size):
            idx_identical = np.random.choice(num_classes, size=num_identical, replace=False)
            predictions[i, idx_identical] = predictions[i, 0]
        targets = np.zeros(batch_size, dtype='int32')

        predictions_th = KTH.variable(predictions, dtype='float32')
        targets_th = KTH.variable(targets, dtype='int32')
        predictions_tf = KTF.variable(predictions, dtype='float32')
        targets_tf = KTF.variable(targets, dtype='int32')

        for k in range(1, num_classes + 1):
            res_th = KTH.eval(KTH.in_top_k(predictions_th, targets_th, k))
            res_tf = KTF.eval(KTF.in_top_k(predictions_tf, targets_tf, k))

            assert res_th.shape == res_tf.shape
            assert_allclose(res_th, res_tf, atol=1e-05)

    def test_conv1d(self):
        # channels_last input shape: (n, length, input_depth)
        input_shape = (4, 8, 2)
        kernel_shape = (3, 2, 3)
        for strides in [1, 2]:
            xval = np.random.random(input_shape)

            xth = KTH.variable(xval)
            xtf = KTF.variable(xval)
            xc = KC.placeholder(input_shape)

            kernel_val = np.random.random(kernel_shape) - 0.5

            kernel_th = KTH.variable(convert_kernel(kernel_val))
            kernel_tf = KTF.variable(kernel_val)
            kernel_c = KC.variable(kernel_val)

            zth = KTH.eval(KTH.conv1d(xth, kernel_th,
                                      strides=strides,
                                      data_format='channels_last'))
            ztf = KTF.eval(KTF.conv1d(xtf, kernel_tf,
                                      strides=strides,
                                      data_format='channels_last'))

            output_cntk = KC.conv1d(xc, kernel_c,
                                    strides=strides,
                                    data_format='channels_last')
            func_cntk = KC.function([xc], [output_cntk, ])
            zc = func_cntk([xval])
            # Keras function return a list, take the first output
            assert len(zc) == 1
            zc = zc[0]

            assert zth.shape == ztf.shape
            assert_allclose(zth, ztf, atol=1e-05)

            assert ztf.shape == zc.shape
            assert_allclose(ztf, zc, atol=1e-05)

    def test_conv2d(self):
        # TF kernel shape: (rows, cols, input_depth, depth)

        # channels_first input shape: (n, input_depth, rows, cols)
        for input_shape in [(2, 3, 4, 5), (2, 3, 5, 6)]:
            for kernel_shape in [(2, 2, 3, 4), (4, 3, 3, 4)]:
                for padding in ['valid', 'same']:
                    xval = np.random.random(input_shape)

                    xth = KTH.variable(xval)
                    xtf = KTF.variable(xval)
                    xc = KC.placeholder(input_shape)

                    kernel_val = np.random.random(kernel_shape) - 0.5

                    kernel_th = KTH.variable(convert_kernel(kernel_val))
                    kernel_tf = KTF.variable(kernel_val)
                    kernel_c = KC.variable(kernel_val)

                    zth = KTH.eval(KTH.conv2d(xth, kernel_th, data_format='channels_first'))
                    ztf = KTF.eval(KTF.conv2d(xtf, kernel_tf, data_format='channels_first'))

                    output_cntk = KC.conv2d(xc, kernel_c, data_format='channels_first')
                    func_cntk = KC.function([xc], [output_cntk, ])
                    zc = func_cntk([xval])
                    # Keras function return a list, take the first output
                    assert len(zc) == 1
                    zc = zc[0]

                    assert zth.shape == ztf.shape
                    assert_allclose(zth, ztf, atol=1e-05)

                    assert ztf.shape == zc.shape
                    assert_allclose(ztf, zc, atol=1e-05)

        input_shape = (1, 6, 5, 3)
        kernel_shape = (3, 3, 3, 2)

        xval = np.random.random(input_shape)

        xth = KTH.variable(xval)
        xtf = KTF.variable(xval)
        xc = KC.placeholder(input_shape)

        kernel_val = np.random.random(kernel_shape) - 0.5

        kernel_th = KTH.variable(convert_kernel(kernel_val))
        kernel_tf = KTF.variable(kernel_val)
        kernel_c = KC.variable(kernel_val)

        # Test invalid use cases
        with pytest.raises(ValueError):
            KTH.conv2d(xth, kernel_th, data_format='channels_middle')
        with pytest.raises(ValueError):
            KTF.conv2d(xtf, kernel_tf, data_format='channels_middle')

        zth = KTH.eval(KTH.conv2d(xth, kernel_th, data_format='channels_last'))
        ztf = KTF.eval(KTF.conv2d(xtf, kernel_tf, data_format='channels_last'))

        output_cntk = KC.conv2d(xc, kernel_c, data_format='channels_last')
        func_cntk = KC.function([xc], [output_cntk, ])
        zc = func_cntk([xval])
        # Keras function return a list, take the first output
        assert len(zc) == 1
        zc = zc[0]

        assert zth.shape == ztf.shape
        assert_allclose(zth, ztf, atol=1e-05)

        assert ztf.shape == zc.shape
        assert_allclose(ztf, zc, atol=1e-05)

    def test_conv3d(self):
        # TH input shape: (samples, input_depth, conv_dim1, conv_dim2, conv_dim3)
        # TF input shape: (samples, conv_dim1, conv_dim2, conv_dim3, input_depth)
        # TH kernel shape: (depth, input_depth, x, y, z)
        # TF kernel shape: (x, y, z, input_depth, depth)

        # test in data_format = channels_first
        for input_shape in [(2, 3, 4, 5, 4), (2, 3, 5, 4, 6)]:
            for kernel_shape in [(2, 2, 2, 3, 4), (3, 2, 4, 3, 4)]:
                xval = np.random.random(input_shape)

                xth = KTH.variable(xval)
                xtf = KTF.variable(xval)
                xc = KC.placeholder(input_shape)

                kernel_val = np.random.random(kernel_shape) - 0.5

                kernel_th = KTH.variable(convert_kernel(kernel_val))
                kernel_tf = KTF.variable(kernel_val)
                kernel_c = KC.variable(kernel_val)

                zth = KTH.eval(KTH.conv3d(xth, kernel_th, data_format='channels_first'))
                ztf = KTF.eval(KTF.conv3d(xtf, kernel_tf, data_format='channels_first'))

                output_cntk = KC.conv3d(xc, kernel_c, data_format='channels_first')
                func_cntk = KC.function([xc], [output_cntk, ])
                zc = func_cntk([xval])
                # Keras function return a list, take the first output
                assert len(zc) == 1
                zc = zc[0]

                assert zth.shape == ztf.shape
                assert_allclose(zth, ztf, atol=1e-05)

                assert ztf.shape == zc.shape
                assert_allclose(ztf, zc, atol=1e-05)

        # test in data_format = channels_last
        input_shape = (1, 2, 2, 2, 1)
        kernel_shape = (2, 2, 2, 1, 1)

        xval = np.random.random(input_shape)

        xth = KTH.variable(xval)
        xtf = KTF.variable(xval)
        xc = KC.placeholder(input_shape)

        kernel_val = np.random.random(kernel_shape) - 0.5

        kernel_th = KTH.variable(convert_kernel(kernel_val))
        kernel_tf = KTF.variable(kernel_val)
        kernel_c = KC.variable(kernel_val)

        # Test invalid use cases
        with pytest.raises(ValueError):
            KTH.conv3d(xth, kernel_th, data_format='channels_middle')
        with pytest.raises(ValueError):
            KTF.conv3d(xtf, kernel_tf, data_format='channels_middle')

        zth = KTH.eval(KTH.conv3d(xth, kernel_th, data_format='channels_last'))
        ztf = KTF.eval(KTF.conv3d(xtf, kernel_tf, data_format='channels_last'))

        output_cntk = KC.conv3d(xc, kernel_c, data_format='channels_last')
        func_cntk = KC.function([xc], [output_cntk, ])
        zc = func_cntk([xval])
        # Keras function return a list, take the first output
        assert len(zc) == 1
        zc = zc[0]

        assert zth.shape == ztf.shape
        assert_allclose(zth, ztf, atol=1e-05)

        assert ztf.shape == zc.shape
        assert_allclose(ztf, zc, atol=1e-05)

    def test_pool2d(self):
        check_single_tensor_operation('pool2d', (5, 10, 12, 3), [KTH, KTF, KCSD], pool_size=(2, 2),
                                      strides=(1, 1), padding='valid')

        check_single_tensor_operation('pool2d', (5, 9, 11, 3), [KTH, KTF, KCSD], pool_size=(2, 2),
                                      strides=(1, 1), padding='valid')

        check_single_tensor_operation('pool2d', (5, 9, 11, 3), [KTH, KTF, KCSD], pool_size=(2, 2),
                                      strides=(1, 1), pool_mode='avg')

        check_single_tensor_operation('pool2d', (5, 9, 11, 3), [KTH, KTF, KCSD], pool_size=(2, 3),
                                      strides=(1, 1), padding='valid')

    def test_pool3d(self):
        check_single_tensor_operation('pool3d', (5, 10, 12, 5, 3), [KTH, KTF, KCSD], pool_size=(2, 2, 2),
                                      strides=(1, 1, 1), padding='valid')

        check_single_tensor_operation('pool3d', (5, 9, 11, 5, 3), [KTH, KTF, KCSD], pool_size=(2, 2, 2),
                                      strides=(1, 1, 1), padding='valid')

        check_single_tensor_operation('pool3d', (5, 9, 11, 5, 3), [KTH, KTF, KCSD], pool_size=(2, 2, 2),
                                      strides=(1, 1, 1), pool_mode='avg')

        check_single_tensor_operation('pool3d', (5, 9, 11, 5, 3), [KTH, KTF, KCSD], pool_size=(2, 3, 2),
                                      strides=(1, 1, 1), padding='valid')

        check_single_tensor_operation('pool3d', (2, 6, 6, 6, 3), [KTH, KTF], pool_size=(3, 3, 3),
                                      strides=(1, 1, 1), padding='same', pool_mode='avg')

    def test_random_normal(self):
        mean = 0.
        std = 1.
        for k in BACKENDS:
            rand = k.eval(k.random_normal((1000, 1000), mean=mean, stddev=std))
            assert rand.shape == (1000, 1000)
            assert np.abs(np.mean(rand) - mean) < 0.01
            assert np.abs(np.std(rand) - std) < 0.01

    def test_random_uniform(self):
        min_val = -1.
        max_val = 1.
        for k in BACKENDS:
            rand = k.eval(k.random_uniform((1000, 1000), min_val, max_val))
            assert rand.shape == (1000, 1000)
            assert np.abs(np.mean(rand)) < 0.01
            assert np.max(rand) <= max_val
            assert np.min(rand) >= min_val

    def test_random_binomial(self):
        p = 0.5
        for k in BACKENDS:
            rand = k.eval(k.random_binomial((1000, 1000), p))
            assert rand.shape == (1000, 1000)
            assert np.abs(np.mean(rand) - p) < 0.01
            assert np.max(rand) == 1
            assert np.min(rand) == 0

    '''need special handle for different backend'''

    def test_internal_conv_utils(self):
        xshape = (5, 4, 3, 2)
        xval = np.random.random(xshape)
        xtf = KTF.variable(xval)
        ztf = KTF._preprocess_deconv_output_shape(xtf, xshape, 'channels_first')
        assert ztf == (5, 3, 2, 4)

        for dtype in [None, 'float64']:
            xval = np.random.random((5, 4, 3, 2))
            xtf = KTF.variable(xval, dtype=dtype)
            ztf = KTF.eval(KTF._preprocess_conv2d_input(xtf, 'channels_first'))
            assert ztf.shape == (5, 3, 2, 4)

            xval = np.random.random((6, 5, 4, 3, 2))
            xtf = KTF.variable(xval, dtype=dtype)
            ztf = KTF.eval(KTF._preprocess_conv3d_input(xtf, 'channels_first'))
            assert ztf.shape == (6, 4, 3, 2, 5)

            xval = np.random.random((5, 4, 3, 2))
            xtf = KTF.variable(xval, dtype=dtype)
            ztf = KTF.eval(KTF._preprocess_conv2d_kernel(xtf, 'channels_first'))
            assert ztf.shape == (3, 2, 4, 5)

            xval = np.random.random((6, 5, 4, 3, 2))
            xtf = KTF.variable(xval, dtype=dtype)
            ztf = KTF.eval(KTF._preprocess_conv3d_kernel(xtf, 'channels_first'))
            assert ztf.shape == (4, 3, 2, 5, 6)

        xval = np.random.random((5, 4, 3, 2))
        xtf = KTF.variable(xval)
        ztf = KTF.eval(KTF._postprocess_conv2d_output(xtf, 'channels_first'))
        assert ztf.shape == (5, 2, 4, 3)

        xval = np.random.random((6, 5, 4, 3, 2))
        xtf = KTF.variable(xval)
        ztf = KTF.eval(KTF._postprocess_conv3d_output(xtf, 'channels_first'))
        assert ztf.shape == (6, 2, 5, 4, 3)

    def test_pooling_invalid_use(self):
        for (input_shape, pool_size) in ([(5, 10, 12, 3), (5, 10, 12, 5, 3)], [(2, 2), (2, 2, 2)]):
            for backend in (KTH, KTF):
                x = backend.variable(np.random.random(input_shape))
                if len(pool_size) == 2:
                    with pytest.raises(ValueError):
                        backend.pool2d(x, pool_size=pool_size, data_format='channels_middle')
                    with pytest.raises(ValueError):
                        backend.pool2d(x, pool_size=pool_size, padding='twice')
                    with pytest.raises(ValueError):
                        backend.pool2d(x, pool_size=pool_size, pool_mode='median')
                else:
                    with pytest.raises(ValueError):
                        backend.pool3d(x, pool_size=pool_size, data_format='channels_middle')
                    with pytest.raises(ValueError):
                        backend.pool3d(x, pool_size=pool_size, padding='twice')
                    with pytest.raises(ValueError):
                        backend.pool3d(x, pool_size=pool_size, pool_mode='median')

    def test_resize_images(self):
        for data_format in ['channels_first', 'channels_last']:
            shape = (5, 5)
            if data_format == 'channels_first':
                x_shape = (2, 3) + shape
            elif data_format == 'channels_last':
                x_shape = (2,) + shape + (3,)
            check_single_tensor_operation('resize_images', x_shape,
                                          [KTH, KTF, KCSD],
                                          height_factor=2,
                                          width_factor=2,
                                          data_format=data_format)

        # Test invalid use cases
        for backend in (KTH, KTF):
            x = backend.variable(np.random.random(x_shape))
            with pytest.raises(ValueError):
                backend.resize_images(x, 2, 2, data_format='channels_middle')

    def test_resize_volumes(self):
        for data_format in ['channels_first', 'channels_last']:
            shape = (5, 5, 5)
            if data_format == 'channels_first':
                x_shape = (2, 3) + shape
            elif data_format == 'channels_last':
                x_shape = (2,) + shape + (3,)
            check_single_tensor_operation('resize_volumes', x_shape,
                                          [KTH, KTF],
                                          depth_factor=2,
                                          height_factor=2,
                                          width_factor=2,
                                          data_format=data_format)

        # Test invalid use cases
        for backend in (KTH, KTF):
            x = backend.variable(np.random.random(x_shape))
            with pytest.raises(ValueError):
                backend.resize_volumes(x, 2, 2, 2, data_format='channels_middle')

    def test_temporal_padding(self):
        check_single_tensor_operation('temporal_padding', (2, 3, 4),
                                      BACKENDS, padding=(2, 2))

    def test_spatial_2d_padding(self):
        for data_format in ['channels_first', 'channels_last']:
            shape = (5, 5)
            padding = ((1, 2), (2, 1))
            if data_format == 'channels_first':
                x_shape = (1, 3) + shape
            else:
                x_shape = (1,) + shape + (3,)
            x = np.random.random(x_shape)
            xth = KTH.variable(x)
            xtf = KTF.variable(x)
            zth = KTH.eval(KTH.spatial_2d_padding(xth, padding=padding, data_format=data_format))
            ztf = KTF.eval(KTF.spatial_2d_padding(xtf, padding=padding, data_format=data_format))
            assert zth.shape == ztf.shape
            assert_allclose(zth, ztf, atol=1e-05)

        # Test invalid use cases
        for backend in (KTH, KTF):
            x = backend.variable(np.random.random(x_shape))
            with pytest.raises(ValueError):
                backend.spatial_2d_padding(x, padding=padding, data_format='channels_middle')

    def test_spatial_3d_padding(self):
        for data_format in ['channels_first', 'channels_last']:
            shape = (5, 5, 5)
            padding = ((1, 2), (2, 1), (1, 2))
            if data_format == 'channels_first':
                x_shape = (1, 3) + shape
            else:
                x_shape = (1,) + shape + (3,)
            check_single_tensor_operation('spatial_3d_padding', x_shape,
                                          BACKENDS,
                                          padding=padding,
                                          data_format=data_format)

        # Test invalid use cases
        for backend in (KTH, KTF):
            x = backend.variable(np.random.random(x_shape))
            with pytest.raises(ValueError):
                backend.spatial_3d_padding(x, padding=padding, data_format='channels_middle')

    def test_bias_add(self):
        for data_format in ['channels_first', 'channels_last']:
            for shape in [(), (3,), (2, 3), (5, 3, 2)]:
                if data_format == 'channels_first':
                    x_shape = (1, 4) + shape
                else:
                    x_shape = (1,) + shape + (4,)
                bias_shape = (4,)
                check_two_tensor_operation('bias_add', x_shape, bias_shape,
                                           [KTH, KTF, KCSD],
                                           data_format=data_format)

            if data_format == 'channels_first':
                x_shape = (20, 6, 10)
            else:
                x_shape = (20, 10, 6)
            check_two_tensor_operation('bias_add', x_shape, (10, 6),
                                       [KTH, KTF, KCSD],
                                       data_format=data_format)

        # Test invalid use casess
        for backend in (KTH, KTF):
            x = backend.variable(np.random.random(x_shape))
            b = backend.variable(np.random.random(bias_shape))
            with pytest.raises(ValueError):
                KTF.bias_add(x, b, data_format='channels_middle')

    def test_batchnorm(self):
        shape = (2, 3)
        for data_format in ['channels_first', 'channels_last']:
            if data_format == 'channels_first':
                x_shape = (1, 4) + shape
            else:
                x_shape = (1,) + shape + (4,)
            xth = KTH.variable(np.random.random(x_shape))
            xtf = KTF.variable(np.random.random(x_shape))
            zth, _, _ = KTH.normalize_batch_in_training(xth, None, None,
                                                        reduction_axes='per-activation')
            ztf, _, _ = KTF.normalize_batch_in_training(xtf, None, None,
                                                        reduction_axes=[0, 1, 2, 3])
            zth = KTH.eval(zth)
            ztf = KTF.eval(ztf)
            assert zth.shape == ztf.shape

    def test_ctc(self):
        # simplified version of TensorFlow's test

        label_lens = np.expand_dims(np.asarray([5, 4]), 1)
        input_lens = np.expand_dims(np.asarray([5, 5]), 1)  # number of timesteps

        # the Theano and TensorFlow CTC code use different methods to ensure
        # numerical stability.  The Theano code subtracts out the max
        # before the final log, so the results are different but scale
        # identically and still train properly
        loss_log_probs_tf = [3.34211, 5.42262]
        loss_log_probs_th = [1.73308, 3.81351]

        # dimensions are batch x time x categories
        labels = np.asarray([[0, 1, 2, 1, 0], [0, 1, 1, 0, -1]])
        inputs = np.asarray(
            [[[0.633766, 0.221185, 0.0917319, 0.0129757, 0.0142857, 0.0260553],
              [0.111121, 0.588392, 0.278779, 0.0055756, 0.00569609, 0.010436],
              [0.0357786, 0.633813, 0.321418, 0.00249248, 0.00272882, 0.0037688],
              [0.0663296, 0.643849, 0.280111, 0.00283995, 0.0035545, 0.00331533],
              [0.458235, 0.396634, 0.123377, 0.00648837, 0.00903441, 0.00623107]],
             [[0.30176, 0.28562, 0.0831517, 0.0862751, 0.0816851, 0.161508],
              [0.24082, 0.397533, 0.0557226, 0.0546814, 0.0557528, 0.19549],
              [0.230246, 0.450868, 0.0389607, 0.038309, 0.0391602, 0.202456],
              [0.280884, 0.429522, 0.0326593, 0.0339046, 0.0326856, 0.190345],
              [0.423286, 0.315517, 0.0338439, 0.0393744, 0.0339315, 0.154046]]],
            dtype=np.float32)

        labels_tf = KTF.variable(labels, dtype="int32")
        inputs_tf = KTF.variable(inputs, dtype="float32")
        input_lens_tf = KTF.variable(input_lens, dtype="int32")
        label_lens_tf = KTF.variable(label_lens, dtype="int32")
        res = KTF.eval(KTF.ctc_batch_cost(labels_tf, inputs_tf, input_lens_tf, label_lens_tf))
        assert_allclose(res[:, 0], loss_log_probs_tf, atol=1e-05)

        labels_th = KTH.variable(labels, dtype="int32")
        inputs_th = KTH.variable(inputs, dtype="float32")
        input_lens_th = KTH.variable(input_lens, dtype="int32")
        label_lens_th = KTH.variable(label_lens, dtype="int32")
        res = KTH.eval(KTH.ctc_batch_cost(labels_th, inputs_th, input_lens_th, label_lens_th))
        assert_allclose(res[0, :], loss_log_probs_th, atol=1e-05)

    '''only tensorflow tested, need special handle'''

    def test_ctc_decode_greedy(self):
        # Test adapted from tensorflow
        """Test two batch entries - best path decoder."""
        max_time_steps = 6

        seq_len_0 = 4
        input_prob_matrix_0 = np.asarray(
            [[1.0, 0.0, 0.0, 0.0],  # t=0
             [0.0, 0.0, 0.4, 0.6],  # t=1
             [0.0, 0.0, 0.4, 0.6],  # t=2
             [0.0, 0.9, 0.1, 0.0],  # t=3
             [0.0, 0.0, 0.0, 0.0],  # t=4 (ignored)
             [0.0, 0.0, 0.0, 0.0]],  # t=5 (ignored)
            dtype=np.float32)
        input_log_prob_matrix_0 = np.log(input_prob_matrix_0)

        seq_len_1 = 5
        # dimensions are time x depth

        input_prob_matrix_1 = np.asarray(
            [[0.1, 0.9, 0.0, 0.0],  # t=0
             [0.0, 0.9, 0.1, 0.0],  # t=1
             [0.0, 0.0, 0.1, 0.9],  # t=2
             [0.0, 0.9, 0.1, 0.1],  # t=3
             [0.9, 0.1, 0.0, 0.0],  # t=4
             [0.0, 0.0, 0.0, 0.0]],  # t=5 (ignored)
            dtype=np.float32)

        # len max_time_steps array of batch_size x depth matrices
        inputs = [np.vstack([input_prob_matrix_0[t, :],
                             input_prob_matrix_1[t, :]])
                  for t in range(max_time_steps)]

        # change tensorflow order to keras backend order
        inputs = KTF.variable(np.asarray(inputs).transpose((1, 0, 2)))
        # batch_size length vector of sequence_lengths
        input_length = KTF.variable(np.array([seq_len_0, seq_len_1], dtype=np.int32))

        # batch_size length vector of negative log probabilities
        log_prob_truth = np.array([
            np.sum(-np.log([1.0, 0.6, 0.6, 0.9])),
            np.sum(-np.log([0.9, 0.9, 0.9, 0.9, 0.9]))
        ], np.float32)[:, np.newaxis]

        # keras output, unlike tensorflow, is a dense (not sparse) tensor
        decode_truth = np.array([[0, 1, -1], [1, 1, 0]])

        decode_pred_tf, log_prob_pred_tf = KTF.ctc_decode(inputs,
                                                          input_length,
                                                          greedy=True)

        assert len(decode_pred_tf) == 1

        decode_pred = KTF.eval(decode_pred_tf[0])
        log_prob_pred = KTF.eval(log_prob_pred_tf)

        assert np.alltrue(decode_truth == decode_pred)
        assert np.allclose(log_prob_truth, log_prob_pred)

    '''tensorflow only, need special handle'''

    def test_ctc_decode_beam_search(self):
        """Test one batch, two beams - hibernating beam search."""

        depth = 6

        seq_len_0 = 5
        input_prob_matrix_0 = np.asarray(
            [[0.30999, 0.309938, 0.0679938, 0.0673362, 0.0708352, 0.173908],
             [0.215136, 0.439699, 0.0370931, 0.0393967, 0.0381581, 0.230517],
             [0.199959, 0.489485, 0.0233221, 0.0251417, 0.0233289, 0.238763],
             [0.279611, 0.452966, 0.0204795, 0.0209126, 0.0194803, 0.20655],
             [0.51286, 0.288951, 0.0243026, 0.0220788, 0.0219297, 0.129878],
             # Random entry added in at time=5
             [0.155251, 0.164444, 0.173517, 0.176138, 0.169979, 0.160671]],
            dtype=np.float32)

        # len max_time_steps array of batch_size x depth matrices
        inputs = ([input_prob_matrix_0[t, :][np.newaxis, :]
                   for t in range(seq_len_0)] +  # Pad to max_time_steps = 8
                  2 * [np.zeros((1, depth), dtype=np.float32)])

        inputs = KTF.variable(np.asarray(inputs).transpose((1, 0, 2)))

        # batch_size length vector of sequence_lengths
        input_length = KTF.variable(np.array([seq_len_0], dtype=np.int32))
        # batch_size length vector of negative log probabilities
        log_prob_truth = np.array([
            0.584855,  # output beam 0
            0.389139  # output beam 1
        ], np.float32)[np.newaxis, :]

        decode_truth = [np.array([1, 0]), np.array([0, 1, 0])]

        beam_width = 2
        top_paths = 2

        decode_pred_tf, log_prob_pred_tf = KTF.ctc_decode(inputs,
                                                          input_length,
                                                          greedy=False,
                                                          beam_width=beam_width,
                                                          top_paths=top_paths)

        assert len(decode_pred_tf) == top_paths

        log_prob_pred = KTF.eval(log_prob_pred_tf)

        for i in range(top_paths):
            assert np.alltrue(decode_truth[i] == KTF.eval(decode_pred_tf[i]))

        assert np.allclose(log_prob_truth, log_prob_pred)

    def test_one_hot(self):
        input_length = 10
        num_classes = 20
        batch_size = 30
        indices = np.random.randint(0, num_classes, size=(batch_size, input_length))
        oh = np.eye(num_classes)[indices]
        for k in BACKENDS:
            koh = k.eval(k.one_hot(k.variable(indices, dtype='int32'), num_classes))
            assert np.all(koh == oh)

    def test_sparse_dot(self):
        x_d = np.array([0, 7, 2, 3], dtype=np.float32)
        x_r = np.array([0, 2, 2, 3], dtype=np.int64)
        x_c = np.array([4, 3, 2, 3], dtype=np.int64)

        x_sparse = sparse.csr_matrix((x_d, (x_r, x_c)), shape=(4, 5))
        x_dense = x_sparse.toarray()

        W = np.random.random((5, 4))
        # cntk not support it yet
        backends = [KTF]
        if KTH.th_sparse_module:
            # Theano has some dependency issues for sparse
            backends.append(KTH)

        for K in backends:
            t_W = K.variable(W)
            k_s = K.eval(K.dot(K.variable(x_sparse), t_W))
            k_d = K.eval(K.dot(K.variable(x_dense), t_W))

            assert k_s.shape == k_d.shape
            assert_allclose(k_s, k_d, atol=1e-05)

    def test_sparse_concat(self):
        x_d = np.array([0, 7, 2, 3], dtype=np.float32)
        x_r = np.array([0, 2, 2, 3], dtype=np.int64)
        x_c = np.array([4, 3, 2, 3], dtype=np.int64)

        x_sparse_1 = sparse.csr_matrix((x_d, (x_r, x_c)), shape=(4, 5))

        x_d = np.array([0, 7, 2, 3], dtype=np.float32)
        x_r = np.array([0, 2, 2, 3], dtype=np.int64)
        x_c = np.array([4, 3, 2, 3], dtype=np.int64)

        x_sparse_2 = sparse.csr_matrix((x_d, (x_r, x_c)), shape=(4, 5))

        x_dense_1 = x_sparse_1.toarray()
        x_dense_2 = x_sparse_2.toarray()

        # cntk not support it yet
        backends = [KTF]
        if KTH.th_sparse_module:
            # Theano has some dependency issues for sparse
            backends.append(KTH)

        for K in backends:
            k_s = K.concatenate([K.variable(x_sparse_1), K.variable(x_sparse_2)])
            assert K.is_sparse(k_s)

            k_s_d = K.eval(k_s)

            k_d = K.eval(K.concatenate([K.variable(x_dense_1), K.variable(x_dense_2)]))

            assert k_s_d.shape == k_d.shape
            assert_allclose(k_s_d, k_d, atol=1e-05)

    def test_map(self):
        x = np.random.rand(10, 3).astype(np.float32)
        for K in [KTH, KTF]:
            vx = K.variable(x)
            kx = K.eval(K.map_fn(K.sum, vx))
            # make sure we can also walk the indexes in tensorflow which we
            # can't without specifying dtype
            kx2 = K.eval(K.map_fn(
                lambda i: K.sum(vx[i]),
                K.arange(10),
                dtype=K.floatx()
            ))

            assert (10,) == kx.shape
            assert (10,) == kx2.shape
            assert_allclose(x.sum(axis=1), kx, atol=1e-05)
            assert_allclose(kx, kx2, atol=1e-05)

    def test_foldl(self):
        x = np.random.rand(10, 3).astype(np.float32)
        for K in [KTH, KTF]:
            kx = K.eval(K.foldl(lambda a, b: a + b, K.variable(x)))

            assert (3,) == kx.shape
            assert_allclose(x.sum(axis=0), kx, atol=1e-05)

    def test_foldr(self):
        # This test aims to make sure that we walk the array from right to left
        # and checks it in the following way: multiplying left to right 1e-40
        # cannot be held into a float32 so it causes an underflow while from
        # right to left we have no such problem and the result is larger
        x = np.array([1e-20, 1e-20, 10, 10, 10], dtype=np.float32)
        for K in [KTH, KTF]:
            vx = K.variable(x)
            p1 = K.eval(K.foldl(lambda a, b: a * b, vx))
            p2 = K.eval(K.foldr(lambda a, b: a * b, vx))

            assert p1 < p2
            assert 9e-38 < p2 <= 1e-37

    def test_arange(self):
        for test_value in (-20, 0, 1, 10):
            a_list = []
            dtype_list = []
            # cntk has issue with negative number
            for k in [KTH, KTF]:
                t = k.arange(test_value)
                a = k.eval(t)
                assert np.array_equal(a, np.arange(test_value))
                dtype_list.append(k.dtype(t))
                a_list.append(a)

            for i in range(len(a_list) - 1):
                assert np.array_equal(a_list[i], a_list[i + 1])

        for start, stop, step in ((0, 5, 1), (-5, 5, 2), (0, 1, 2)):
            a_list = []
            for k in [KTH, KTF]:
                a = k.eval(k.arange(start, stop, step))
                assert np.array_equal(a, np.arange(start, stop, step))
                a_list.append(a)
            for i in range(len(a_list) - 1):
                assert np.array_equal(a_list[i], a_list[i + 1])

        for dtype in ('int32', 'int64', 'float32', 'float64'):
            for backend in [KTH, KTF]:
                t = backend.arange(10, dtype=dtype)
                assert backend.dtype(t) == dtype

    def test_in_train_phase(self):
        xval = np.random.random((3, 3))
        xth = KTH.variable(xval)
        xtf = KTF.variable(xval)
        yval = np.random.random((2, 2))
        yth = KTH.variable(yval)
        ytf = KTF.variable(yval)

        for training in [True, False]:
            zth = KTH.eval(KTH.in_train_phase(xth, yth, training=training))
            ztf = KTF.eval(KTF.in_train_phase(xtf, ytf, training=training))
            assert zth.shape == ztf.shape
            zth = KTH.eval(KTH.in_train_phase(lambda: xth, lambda: yth, training=training))
            ztf = KTF.eval(KTF.in_train_phase(lambda: xtf, lambda: ytf, training=training))
            assert zth.shape == ztf.shape

    def test_setfloatx_incorrect_values(self):
        # Keep track of the old value
        old_floatx = floatx()
        # Try some incorrect values
        initial = floatx()
        for value in ['', 'beerfloat', 123]:
            with pytest.raises(ValueError):
                set_floatx(value)
        assert floatx() == initial
        # Restore old value
        set_floatx(old_floatx)

    def test_setfloatx_correct_values(self):
        # Keep track of the old value
        old_floatx = floatx()
        # Check correct values
        for value in ['float16', 'float32', 'float64']:
            set_floatx(value)
            assert floatx() == value
        # Restore old value
        set_floatx(old_floatx)

    @pytest.mark.skipif((K.backend() == 'cntk'),
                        reason='cntk does not support float16')
    def test_set_floatx(self):
        """
        Make sure that changes to the global floatx are effectively
        taken into account by the backend.
        """
        # Keep track of the old value
        old_floatx = floatx()

        set_floatx('float16')
        var = variable([10])
        check_dtype(var, 'float16')

        set_floatx('float64')
        var = variable([10])
        check_dtype(var, 'float64')

        # Restore old value
        set_floatx(old_floatx)


if __name__ == '__main__':
    pytest.main([__file__])
